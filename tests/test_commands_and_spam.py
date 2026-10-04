import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import GetChatMember
from aiogram.types import Message, User
from peewee import SqliteDatabase
from pydantic import ValidationError

from app.config import BotConfig, Config
from app.filters.lulu import LuluFilter
from app.handlers.users.commands.settings.setting import router
from database.models.setting import Setting


class CommandTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = Bot('123456:TEST_TOKEN')
        self.config = Config(bot=BotConfig(token='test'))
        self.db = SqliteDatabase(':memory:')
        self.binding = self.db.bind_ctx([Setting])
        self.binding.__enter__()
        self.db.create_tables([Setting])
        self.answer_patch = patch.object(Message, 'answer', new_callable=AsyncMock)
        self.answer = self.answer_patch.start()
        self.member_patch = patch.object(self.bot, 'get_chat_member', new_callable=AsyncMock)
        self.member = self.member_patch.start()
        self.member.return_value = SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR)
        self.me_patch = patch.object(self.bot, 'me', new_callable=AsyncMock)
        self.me_patch.start().return_value = User(id=123456, is_bot=True, first_name='Lulu', username='LuluTestBot')

    async def asyncTearDown(self):
        self.me_patch.stop()
        self.member_patch.stop()
        self.answer_patch.stop()
        self.binding.__exit__(None, None, None)
        self.db.close()
        await self.bot.session.close()

    def message(self, text, **extra):
        return Message.model_validate({
            'message_id':1, 'date':datetime.now(timezone.utc),
            'chat':{'id':-1001234567890, 'type':'supergroup', 'title':'Test'},
            'from':{'id':7, 'is_bot':False, 'first_name':'Admin'},
            'text':text, **extra,
        }).as_(self.bot)

    async def route(self, text, **extra):
        await router.propagate_event('message', self.message(text, **extra), bot=self.bot, config=self.config)

    async def test_filter_arguments_and_boundaries(self):
        f = LuluFilter(command=['protect', 'включить защиту'])
        for text in ['Лулу protect AntiSpam ВКЛ', '  Lulu,  protect AntiSpam\nВКЛ']:
            self.assertEqual((await f(self.message(text)))['lulu_args'], ['AntiSpam','ВКЛ'])
        for text in ['лулуprotect antispam вкл', 'Лулу protectXYZ antispam вкл', 'protect antispam вкл', None]:
            self.assertFalse(await f(self.message(text)))
        self.assertEqual((await f(self.message('Лулу включить защиту welcome')))['lulu_args'], ['welcome'])
        self.assertEqual((await LuluFilter('protect', is_equals=True)(self.message('Лулу protect')))['lulu_args'], [])
        self.assertFalse(await LuluFilter('protect', is_equals=True)(self.message('Лулу protect extra')))
        self.assertEqual((await LuluFilter('protect', ignore_name=True)(self.message('protect X')))['lulu_args'], ['X'])
        self.assertFalse(await LuluFilter('protect', ignore_case=False)(self.message('лулу PROTECT')))
        results = await asyncio.gather(*(f(self.message(f'Лулу protect {i}')) for i in range(10)))
        self.assertEqual([r['lulu_args'] for r in results], [[str(i)] for i in range(10)])

    async def test_named_commands_update_same_setting(self):
        for text, expected in [('лулу защита антиспам вкл',True),
                               ('Лулу защита АНТИСПАМ ВЫКЛ',False),
                               ('Lulu, защита antispam включить',True),
                               ('Лулу защита антиспам выключить',False)]:
            await self.route(text)
            self.assertEqual(Setting.select().count(),1)
            self.assertIs(Setting.get().enabled,expected)

    async def test_invalid_commands_do_not_write(self):
        for text in ['Лулу защита', 'Лулу защита антиспам maybe', 'Лулу защита unknown вкл',
                     'Лулу защита антиспам вкл extra', '/protect antispam вкл', 'лулузащита антиспам вкл']:
            await self.route(text)
        self.assertEqual(Setting.select().count(),0)

    async def test_permissions_fail_closed(self):
        self.member.return_value = SimpleNamespace(status=ChatMemberStatus.MEMBER)
        await self.route('Лулу защита антиспам вкл')
        self.assertEqual(Setting.select().count(),0)
        self.member.side_effect = TelegramBadRequest(method=GetChatMember(chat_id=-1,user_id=7),message='Unavailable')
        await self.route('Лулу защита антиспам вкл')
        self.assertEqual(Setting.select().count(),0)

    async def test_anonymous_admin_and_private_chat(self):
        await self.route('Лулу защита welcome вкл',sender_chat={'id':-1001234567890,'type':'supergroup','title':'Test'})
        self.assertEqual(Setting.get().protection,'welcome')
        self.member.assert_not_called()
        await self.route('Лулу защита антиспам вкл',chat={'id':7,'type':'private','first_name':'Test'})
        self.assertEqual(Setting.select().count(),1)


class ProbabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_probability_and_threshold(self):
        import torch
        from app.utils import predict as prediction
        from app.handlers.users.settings import antispam
        logits = torch.tensor([[0., 2.]])
        fake_model = SimpleNamespace(config=SimpleNamespace(label2id={'spam':0,'ham':1}))
        from unittest.mock import Mock
        fake_model = Mock(config=fake_model.config, return_value=SimpleNamespace(logits=logits))
        with patch.object(prediction,'model',fake_model), patch.object(prediction,'tokenizer',return_value={}):
            probability = prediction.predict('text')
            self.assertAlmostEqual(probability, float(logits.softmax(-1)[0,0]),places=6)
            self.assertGreater(probability,0)
            self.assertLess(probability,1)
        config = Config(bot=BotConfig(token='test',spam_threshold=.9))
        message = SimpleNamespace(from_user=None,chat=SimpleNamespace(id=-1),text='text',caption=None,
                                  reply=AsyncMock(return_value=SimpleNamespace(delete=AsyncMock())),delete=AsyncMock())
        with patch.object(Setting,'is_enabled',new=AsyncMock(return_value=True)), patch.object(antispam,'predict') as predict, patch.object(antispam.asyncio,'sleep',new=AsyncMock()):
            for value, deleted in [(.89,False),(.9,True)]:
                message.delete.reset_mock()
                predict.return_value=value
                await antispam.cmd_antispam_detect_handler(message,config)
                self.assertEqual(message.delete.await_count,int(deleted))
        for invalid in [0,-.1,1.1,float('nan')]:
            with self.assertRaises(ValidationError):
                BotConfig(token='test',spam_threshold=invalid)


if __name__ == '__main__':
    unittest.main()
