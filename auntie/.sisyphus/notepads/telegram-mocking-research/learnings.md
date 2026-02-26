# Python-Telegram-Bot Mocking & Testing Patterns

## Research Summary

### Two Main Approaches for Testing PTB Applications

1. **Pure Mocking (ptbtest)** - Uses Mockbot and generators to create fake Telegram objects
2. **Server-based Mocking (telegram-bot-unittest)** - Runs a Flask server that mimics Telegram API

### Key Libraries

- **ptbtest**: Official test suite for python-telegram-bot
  - Provides Mockbot - fake bot that mimics telegram.Bot API
  - Generators for Update, Message, User, Chat, CallbackQuery
  - No real network calls, completely offline
  
- **telegram-bot-unittest**: Third-party integration testing framework
  - Runs mock Telegram server on localhost
  - Full end-to-end testing with actual HTTP calls
  - Better for integration testing, slower than pure mocks

## Mockbot Capabilities (ptbtest)

Mockbot provides:
- `sent_messages` property - captures all outgoing messages
- `insertUpdate(update)` - injects updates into the bot
- Full API mocking: sendMessage, sendPhoto, editMessageText, etc.
- Automatic Message object generation from responses

## Generator Classes (ptbtest)

- **MessageGenerator** - Creates telegram.Message objects
- **UserGenerator** - Creates telegram.User with random names
- **ChatGenerator** - Creates telegram.Chat objects  
- **CallbackQueryGenerator** - Creates callback query updates
- **UpdateGenerator** - Decorator for wrapping in telegram.Update

### Usage Pattern
```python
from ptbtest import Mockbot, MessageGenerator, UserGenerator, ChatGenerator

bot = Mockbot()
mg = MessageGenerator(bot)
ug = UserGenerator()
cg = ChatGenerator()

# Create test data
user = ug.get_user(first_name="Test", last_name="User")
chat = cg.get_chat(user=user)
update = mg.get_message(user=user, chat=chat, text="/start")
```

## Testing Handler Functions Directly

Best practice: Test handler logic in isolation without full Application setup:

```python
async def test_start_handler():
    # Arrange
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.mention_markdown_v2.return_value = "TestUser"
    update.message.reply_markdown_v2 = AsyncMock()
    
    context = MagicMock()
    
    # Act
    await start(update, context)
    
    # Assert
    update.message.reply_markdown_v2.assert_called_once()
```

## CallbackContext Properties

Key context properties available in handlers:
- `context.bot` - The Bot instance
- `context.args` - Command arguments (list)
- `context.user_data` - Persistent user data dict
- `context.chat_data` - Persistent chat data dict
- `context.bot_data` - Persistent bot-wide data dict
- `context.matches` - Regex match objects
- `context.job` - Present in job callbacks
- `context.error` - Present in error handlers

## Best Practices Learned

1. **Separate handler logic from bot setup** - Makes testing much easier
2. **Use ptbtest for unit tests** - Fast, no network dependencies
3. **Use telegram-bot-unittest for integration tests** - Real HTTP flow
4. **Mock at the right level** - Either mock Update/Context or use Mockbot
5. **Always clean up** - Call updater.stop() after tests
6. **Use pytest fixtures** - For bot setup and teardown

## Official Documentation

- Testing docs: https://docs.python-telegram-bot.org/en/stable/testing.html
- CallbackContext: https://docs.python-telegram-bot.org/en/stable/telegram.ext.callbackcontext.html
- Examples: https://docs.python-telegram-bot.org/en/stable/examples.html

