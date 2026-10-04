from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage
from aiogram.types import Message, User
from peewee import SqliteDatabase
from playhouse.migrate import SqliteMigrator, migrate

from app.config import BotConfig, Config
from app.handlers.users.commands import get_commands_handlers
from app.handlers.users.protects import welcome
from app.utils.welcome import render_welcome
from database import init_database
from database.models.chats import Chats
from database.models.protects import Protects
from database.models.user import User as DatabaseUser


class WelcomeTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = get_commands_handlers()

    async def asyncSetUp(self):
        self.db = SqliteDatabase(':memory:')
        self.binding = self.db.bind_ctx([Chats, Protects])
        self.binding.__enter__()
        self.db.create_tables([Chats, Protects])
        self.bot = Bot('123456:TEST_TOKEN')
        self.patches = [patch.object(welcome,'db',self.db),
                        patch.object(Message,'answer',new_callable=AsyncMock),
                        patch.object(self.bot,'get_chat_member',new_callable=AsyncMock)]
        _,self.answer,self.member = [p.start() for p in self.patches]
        self.member.return_value = SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR)
        self.config = Config(bot=BotConfig(token='test'))

    async def asyncTearDown(self):
        for p in reversed(self.patches): p.stop()
        self.binding.__exit__(None,None,None)
        self.db.close()
        await self.bot.session.close()

    def message(self,text=None,**extra):
        return Message.model_validate({'message_id':1,'date':datetime.now(timezone.utc),
            'chat':{'id':-1001,'type':'supergroup','title':'Test'},
            'from':{'id':7,'is_bot':False,'first_name':'Анна','last_name':'Тест'},
            'text':text,**extra}).as_(self.bot)

    async def route(self,message):
        await self.router.propagate_event('message',message,bot=self.bot,config=self.config)

    async def test_template_and_join_event_through_router(self):
        template='<tg-emoji emoji-id="5278611606756942667">❤️</tg-emoji> Привет! {имя}\n  {фамилия} {ид} {айди} {имяфамилия}'
        await self.route(self.message('лулу настройки приветствие '+template))
        self.assertEqual(Chats.get().welcome_template,template)
        self.assertTrue(await Protects.is_enabled(-1001,'welcome'))
        self.answer.reset_mock()
        user=User(id=42,is_bot=False,first_name='Иван <&>',last_name='Тест')
        await self.route(self.message(new_chat_members=[user]))
        self.answer.assert_awaited_once_with(render_welcome(template,user),parse_mode='HTML')
        await self.route(self.message('Лулу защита приветствие выкл'))
        self.assertFalse(await Protects.is_enabled(-1001,'welcome'))
        self.answer.reset_mock()
        await self.route(self.message(new_chat_members=[user]))
        self.answer.assert_not_awaited()

    async def test_formatted_custom_emoji_utf16_offsets(self):
        prefix='Лулу настройки приветствие '
        text=prefix+'❤️ Привет, {имя}!'
        offset=len(prefix.encode('utf-16-le'))//2
        await self.route(self.message(text,entities=[{'type':'custom_emoji','offset':offset,'length':2,'custom_emoji_id':'5278611606756942667'}]))
        self.assertIn('<tg-emoji emoji-id="5278611606756942667">❤️</tg-emoji>',Chats.get().welcome_template)

    async def test_permissions_and_invalid_templates_preserve_setting(self):
        await self.route(self.message('Лулу настройки приветствие Привет, {имя}!'))
        original=Chats.get().welcome_template
        self.member.return_value=SimpleNamespace(status=ChatMemberStatus.MEMBER)
        await self.route(self.message('Лулу настройки приветствие Другое'))
        self.assertEqual(Chats.get().welcome_template,original)
        self.member.return_value=SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR)
        for text in ['', 'Привет {неизвестно}', 'x'*4097]:
            await self.route(self.message('Лулу настройки приветствие '+text))
            self.assertEqual(Chats.get().welcome_template,original)
        self.answer.side_effect=[TelegramBadRequest(method=SendMessage(chat_id=-1001,text='test'),message='Bad HTML'),None]
        await self.route(self.message('Лулу настройки приветствие <b>сломано'))
        self.assertEqual(Chats.get().welcome_template,original)

    async def test_chats_multiple_members_and_bots(self):
        await self.route(self.message('Лулу настройки приветствие A {имя}'))
        other=self.message('Лулу настройки приветствие B {имя}',chat={'id':-1002,'type':'supergroup','title':'Other'})
        await self.route(other)
        self.assertEqual(Chats.get(Chats.chat_id==-1001).welcome_template,'A {имя}')
        self.assertEqual(Chats.get(Chats.chat_id==-1002).welcome_template,'B {имя}')
        self.answer.reset_mock()
        await self.route(self.message(new_chat_members=[User(id=1,is_bot=False,first_name='Один'),User(id=2,is_bot=False,first_name='Два'),User(id=3,is_bot=True,first_name='Бот')]))
        self.assertEqual([c.args[0] for c in self.answer.await_args_list],['A Один','A Два'])


class WelcomeDataTests(unittest.TestCase):
    def test_placeholders_escape_names_and_optional_last_name(self):
        user=User(id=42,is_bot=False,first_name='<b>A&B</b>')
        self.assertEqual(render_welcome('{имя}|{фамилия}|{ид}|{айди}|{имяфамилия}',user),
                         '&lt;b&gt;A&amp;B&lt;/b&gt;||42|42|&lt;b&gt;A&amp;B&lt;/b&gt;')

    def test_existing_database_migration_is_idempotent(self):
        db=SqliteDatabase(':memory:')
        with db.bind_ctx([DatabaseUser,Chats,Protects]),patch('database.loader.db',db):
            db.create_tables([Chats,Protects])
            Chats.create(chat_id=-1001,chat_name='Preserved')
            Protects.create(chat_id=-1001,protection='antispam',enabled=True)
            migrate(SqliteMigrator(db).drop_column('chats','welcome_template'))
            init_database()
            init_database()
            self.assertEqual(Chats.get().chat_name,'Preserved')
            self.assertIsNone(Chats.get().welcome_template)
            self.assertTrue(Protects.get().enabled)
            self.assertEqual(Chats.select().count(),1)
        db.close()


if __name__=='__main__':
    unittest.main()
