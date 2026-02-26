# Testing python-telegram-bot Applications: Mock/Standalone Mode Guide

This guide covers practical patterns for testing python-telegram-bot applications offline without connecting to Telegram servers.

## Table of Contents

1. [Overview of Approaches](#overview-of-approaches)
2. [Mocking Update and Context Objects](#mocking-update-and-context-objects)
3. [Using ptbtest Library](#using-ptbtest-library)
4. [Testing Handlers with pytest](#testing-handlers-with-pytest)
5. [Integration Testing with telegram-bot-unittest](#integration-testing)
6. [Complete Working Examples](#complete-working-examples)
7. [Best Practices](#best-practices)

---

## Overview of Approaches

### Approach 1: Pure Unit Testing (Fastest)
Mock Update and CallbackContext objects directly using `unittest.mock`.

### Approach 2: Using ptbtest Library (Recommended)
Use the official test suite `ptbtest` with Mockbot and generators.

### Approach 3: Integration Testing
Use `telegram-bot-unittest` to test full HTTP flow with a mock server.

---

## Mocking Update and Context Objects

### Method 1: Direct Mocking with unittest.mock

```python
import pytest
from unittest.mock import MagicMock, AsyncMock
import pytest_asyncio


# Your handler function
async def start(update, context):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_markdown_v2(
        fr'Hi {user.mention_markdown_v2()}!',
        reply_markup=ForceReply(selective=True),
    )


class TestHandlersDirectMock:
    """Test handlers by directly mocking Update and Context."""
    
    @pytest_asyncio.fixture
    def mock_update(self):
        """Create a mock Update object."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.mention_markdown_v2.return_value = "TestUser"
        update.effective_user.id = 123456
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"
        update.effective_user.username = "testuser"
        update.message = AsyncMock()
        update.message.text = "/start"
        update.message.chat = MagicMock()
        update.message.chat.id = 123456
        update.message.chat.type = "private"
        return update
    
    @pytest_asyncio.fixture
    def mock_context(self):
        """Create a mock CallbackContext."""
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        context.args = []
        context.user_data = {}
        context.chat_data = {}
        context.bot_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_start_handler(self, mock_update, mock_context):
        """Test the /start command handler."""
        # Act
        await start(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_markdown_v2.assert_called_once()
        call_args = mock_update.message.reply_markdown_v2.call_args
        assert "Hi TestUser" in call_args[0][0]
```

### Method 2: Using Real Telegram Objects

```python
from telegram import Update, User, Chat, Message, ForceReply
from telegram.ext import CallbackContext


def create_test_update(text: str, user_id: int = 123456) -> Update:
    """Create a real Update object with User, Chat, and Message."""
    user = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="testuser",
        is_bot=False
    )
    
    chat = Chat(
        id=user_id,
        type="private",
        first_name="Test",
        last_name="User",
        username="testuser"
    )
    
    message = Message(
        message_id=1,
        from_user=user,
        chat=chat,
        date=datetime.now(),
        text=text
    )
    
    return Update(
        update_id=1,
        message=message
    )
```

---

## Using ptbtest Library

### Installation

```bash
pip install ptbtest
```

### Basic Usage

```python
import pytest
import pytest_asyncio
from ptbtest import Mockbot, MessageGenerator, UserGenerator, ChatGenerator
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


class TestWithPtbtest:
    """Tests using ptbtest library."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a Mockbot instance."""
        return Mockbot()
    
    @pytest.fixture
    def generators(self, mock_bot):
        """Create generators for test data."""
        return {
            'user': UserGenerator(),
            'chat': ChatGenerator(),
            'message': MessageGenerator(mock_bot)
        }
    
    def test_help_command(self, mock_bot, generators):
        """Test help command handler."""
        # Arrange
        def help_handler(update, context):
            update.message.reply_text('Help!')
        
        updater = Updater(bot=mock_bot)
        updater.dispatcher.add_handler(CommandHandler("help", help_handler))
        updater.start_polling()
        
        # Create test message
        update = generators['message'].get_message(text="/help")
        
        # Act
        mock_bot.insertUpdate(update)
        
        # Assert
        assert len(mock_bot.sent_messages) == 1
        sent = mock_bot.sent_messages[0]
        assert sent['method'] == "sendMessage"
        assert sent['text'] == "Help!"
        
        updater.stop()
    
    def test_echo_handler(self, mock_bot, generators):
        """Test echo handler with multiple messages."""
        # Arrange
        def echo_handler(update, context):
            update.message.reply_text(update.message.text)
        
        updater = Updater(bot=mock_bot)
        updater.dispatcher.add_handler(
            MessageHandler(Filters.text & ~Filters.command, echo_handler)
        )
        updater.start_polling()
        
        # Create test messages
        update1 = generators['message'].get_message(text="Hello")
        update2 = generators['message'].get_message(text="World")
        
        # Act
        mock_bot.insertUpdate(update1)
        mock_bot.insertUpdate(update2)
        
        # Assert
        assert len(mock_bot.sent_messages) == 2
        assert mock_bot.sent_messages[0]['text'] == "Hello"
        assert mock_bot.sent_messages[1]['text'] == "World"
        
        updater.stop()
    
    def test_custom_user_and_chat(self, mock_bot, generators):
        """Test with specific user and chat configuration."""
        # Create specific test user
        user = generators['user'].get_user(
            first_name="Alice",
            last_name="Smith",
            username="alice_smith",
            id=999999
        )
        
        # Create group chat
        chat = generators['chat'].get_chat(
            type="group",
            title="Test Group"
        )
        
        # Create message with custom user in group
        update = generators['message'].get_message(
            user=user,
            chat=chat,
            text="/start"
        )
        
        assert update.message.from_user.first_name == "Alice"
        assert update.message.chat.type == "group"
```

### Testing Callback Queries

```python
from ptbtest import CallbackQueryGenerator


def test_callback_query(mock_bot, generators):
    """Test callback query handling."""
    # Arrange
    def button_handler(update, context):
        query = update.callback_query
        query.answer()
        query.edit_message_text(text=f"Selected: {query.data}")
    
    updater = Updater(bot=mock_bot)
    updater.dispatcher.add_handler(
        CallbackQueryHandler(button_handler)
    )
    updater.start_polling()
    
    # Create callback query
    cq_gen = CallbackQueryGenerator(mock_bot)
    update = cq_gen.get_callback_query(data="option_1")
    
    # Act
    mock_bot.insertUpdate(update)
    
    # Assert
    assert len(mock_bot.sent_messages) >= 1
    
    updater.stop()
```

---

## Testing Handlers with pytest

### Recommended: Separate Handler Logic

Structure your bot for testability:

```python
# bot_handlers.py - Pure logic, no bot setup
from telegram import Update, ForceReply
from telegram.ext import CallbackContext


async def start(update: Update, context: CallbackContext) -> None:
    """Send welcome message."""
    user = update.effective_user
    await update.message.reply_markdown_v2(
        fr'Hi {user.mention_markdown_v2()}! Welcome to the bot.',
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: CallbackContext) -> None:
    """Send help message."""
    await update.message.reply_text('Available commands:\n/start - Start bot\n/help - Show help')


async def echo(update: Update, context: CallbackContext) -> None:
    """Echo user message."""
    await update.message.reply_text(update.message.text)


# bot_main.py - Bot setup and execution
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot_handlers import start, help_command, echo


def create_application(token: str) -> Application:
    """Create and configure the Application."""
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    return application


def main():
    """Run the bot."""
    import os
    token = os.getenv("BOT_TOKEN")
    app = create_application(token)
    app.run_polling()


if __name__ == "__main__":
    main()
```

### Testing with pytest-asyncio

```python
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from bot_handlers import start, help_command, echo


@pytest_asyncio.fixture
def mock_update():
    """Create a mock Update object with all needed attributes."""
    update = MagicMock(spec=Update)
    
    # User configuration
    update.effective_user = MagicMock()
    update.effective_user.id = 123456
    update.effective_user.first_name = "John"
    update.effective_user.last_name = "Doe"
    update.effective_user.username = "johndoe"
    update.effective_user.mention_markdown_v2.return_value = "[John Doe](tg://user?id=123456)"
    
    # Message configuration
    update.message = AsyncMock()
    update.message.message_id = 1
    update.message.text = "/start"
    update.message.date = MagicMock()
    update.message.chat = MagicMock()
    update.message.chat.id = 123456
    update.message.chat.type = "private"
    
    return update


@pytest_asyncio.fixture
def mock_context():
    """Create a mock CallbackContext."""
    context = MagicMock(spec=CallbackContext)
    context.bot = MagicMock()
    context.args = []
    context.user_data = {}
    context.chat_data = {}
    context.bot_data = {}
    context.matches = None
    return context


class TestBotHandlers:
    """Test suite for bot handlers."""
    
    @pytest.mark.asyncio
    async def test_start_sends_welcome_message(self, mock_update, mock_context):
        """Test that /start sends welcome message."""
        await start(mock_update, mock_context)
        
        mock_update.message.reply_markdown_v2.assert_called_once()
        call_args = mock_update.message.reply_markdown_v2.call_args
        
        assert "Hi" in call_args[0][0]
        assert "Welcome to the bot" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_help_shows_commands(self, mock_update, mock_context):
        """Test that /help displays available commands."""
        await help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        
        assert "/start" in call_args[0][0]
        assert "/help" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_echo_repeats_text(self, mock_update, mock_context):
        """Test that echo handler repeats user text."""
        test_message = "Hello, this is a test!"
        mock_update.message.text = test_message
        
        await echo(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once_with(test_message)
    
    @pytest.mark.asyncio
    async def test_start_with_different_users(self):
        """Test /start with various user configurations."""
        test_cases = [
            {"first_name": "Alice", "last_name": "Smith", "id": 111},
            {"first_name": "Bob", "last_name": None, "id": 222},
            {"first_name": "Charlie", "last_name": "Brown", "id": 333},
        ]
        
        for user_data in test_cases:
            update = MagicMock()
            update.effective_user = MagicMock()
            update.effective_user.id = user_data["id"]
            update.effective_user.first_name = user_data["first_name"]
            update.effective_user.last_name = user_data["last_name"]
            update.effective_user.mention_markdown_v2.return_value = f"[{user_data['first_name']}](tg://user?id={user_data['id']})"
            update.message = AsyncMock()
            
            context = MagicMock()
            
            await start(update, context)
            
            assert update.message.reply_markdown_v2.called
```

---

## Integration Testing

### Using telegram-bot-unittest

```bash
pip install telegram-bot-unittest
```

```python
# conftest.py
import pytest
from telegram_bot_unittest.fixtures import telegram_server, user

pytest_plugins = ['telegram_bot_unittest.fixtures']
```

```python
# fixtures.py
import pytest
from telegram_bot_unittest.routes import TELEGRAM_URL
from telegram_bot_unittest.user import BOT_TOKEN
from bot_main import create_application


@pytest.fixture(scope='session')
def bot(telegram_server):
    """Create bot connected to mock server."""
    application = create_application(BOT_TOKEN)
    # Override base URL to point to mock server
    application.bot.base_url = TELEGRAM_URL
    application.run_polling()
    yield application.bot
    application.stop()
```

```python
# test_integration.py

def test_e2e_start_command(bot, user):
    """End-to-end test of /start command."""
    user.send_command('/start')
    message = user.get_message()
    
    assert message is not None
    assert 'Hi' in message['text']


def test_e2e_echo_message(bot, user):
    """End-to-end test of echo functionality."""
    test_text = "Hello from test!"
    user.send_message(test_text)
    
    message = user.get_message()
    assert message['text'] == test_text
```

---

## Complete Working Examples

### Example 1: Simple Bot with Full Test Suite

```python
# simple_bot.py
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}! Welcome!"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"Chat ID: {chat_id}\nUser ID: {user_id}"
    )


def get_application(token: str) -> Application:
    """Create application for testing."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    return app
```

```python
# test_simple_bot.py
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from simple_bot import start, status


class TestSimpleBot:
    """Comprehensive tests for simple bot."""
    
    @pytest_asyncio.fixture
    def update(self):
        """Create mock update."""
        u = MagicMock()
        u.effective_user = MagicMock()
        u.effective_user.first_name = "Test"
        u.effective_user.id = 123
        u.effective_chat = MagicMock()
        u.effective_chat.id = 456
        u.message = AsyncMock()
        return u
    
    @pytest_asyncio.fixture
    def context(self):
        """Create mock context."""
        return MagicMock()
    
    @pytest.mark.asyncio
    async def test_start_sends_personalized_greeting(self, update, context):
        """Test that start command includes user's name."""
        await start(update, context)
        
        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert "Hello Test" in text
        assert "Welcome" in text
    
    @pytest.mark.asyncio
    async def test_status_shows_ids(self, update, context):
        """Test that status shows chat and user IDs."""
        await status(update, context)
        
        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert "456" in text  # chat_id
        assert "123" in text  # user_id
```

### Example 2: Testing with Real Objects (No Mocks)

```python
# test_with_real_objects.py
from datetime import datetime
from telegram import Update, User, Chat, Message
from telegram.ext import CallbackContext


def create_real_update(
    text: str,
    user_id: int = 123456,
    first_name: str = "Test",
    chat_type: str = "private"
) -> Update:
    """Create Update with real Telegram objects."""
    
    user = User(
        id=user_id,
        first_name=first_name,
        is_bot=False,
        username=f"user_{user_id}"
    )
    
    chat = Chat(
        id=user_id if chat_type == "private" else -100123456,
        type=chat_type
    )
    
    message = Message(
        message_id=1,
        from_user=user,
        chat=chat,
        date=datetime.now(),
        text=text
    )
    
    return Update(
        update_id=1,
        message=message
    )


# Usage in test
@pytest.mark.asyncio
async def test_with_real_objects():
    """Test using real Telegram objects."""
    update = create_real_update("/start", user_id=999, first_name="Alice")
    
    # Verify real objects work correctly
    assert update.message.text == "/start"
    assert update.message.from_user.first_name == "Alice"
    assert update.message.from_user.id == 999
```

---

## Best Practices

### 1. **Structure for Testability**
```python
# Good: Separate handlers from setup
# handlers.py
async def my_handler(update, context):
    pass

# main.py
def create_app(token):
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("cmd", my_handler))
    return app
```

### 2. **Use pytest Fixtures**
```python
@pytest.fixture
def mock_bot():
    return Mockbot()

@pytest.fixture
def mock_update():
    # Setup common update structure
    pass
```

### 3. **Test Async Handlers Properly**
```python
@pytest.mark.asyncio
async def test_async_handler():
    await handler(update, context)
```

### 4. **Verify Bot Interactions**
```python
# Check what was sent
assert len(mock_bot.sent_messages) == 1
assert mock_bot.sent_messages[0]['method'] == 'sendMessage'
```

### 5. **Reset State Between Tests**
```python
def setup_method(self):
    self.bot.reset()  # Clear sent_messages
```

### 6. **Use Parametrize for Multiple Cases**
```python
@pytest.mark.parametrize("command,expected", [
    ("/start", "Welcome"),
    ("/help", "Help"),
])
async def test_commands(command, expected):
    # Test both commands
    pass
```

### 7. **Mock External Services**
```python
@pytest.fixture(autouse=True)
def mock_external_api():
    with patch('my_bot.requests.get') as mock:
        mock.return_value.json.return_value = {"data": "test"}
        yield mock
```

---

## Summary

| Approach | Speed | Complexity | Use Case |
|----------|-------|------------|----------|
| Direct Mocking | ⚡⚡⚡ | Low | Unit tests, TDD |
| ptbtest Library | ⚡⚡ | Medium | Handler testing, integration |
| telegram-bot-unittest | ⚡ | High | E2E tests, full flow |

**Recommended**: Use direct mocking for most tests, ptbtest for complex handler scenarios, and server-based testing only when absolutely necessary.

---

## References

- **ptbtest**: https://github.com/python-telegram-bot/ptbtest
- **telegram-bot-unittest**: https://github.com/dontsovcmc/telegram-bot-unittest
- **PTB Testing Docs**: https://docs.python-telegram-bot.org/en/stable/testing.html
- **PTB Examples**: https://docs.python-telegram-bot.org/en/stable/examples.html
