# Auntie - Personal Telegram Bot

A personal Telegram bot for automation and assistance.

## Features

- Conversational interface via Telegram
- Extensible skill system
- SQLite database with conversation history
- Configurable via environment variables

## Quick Start

1. Copy and configure environment:
   ```bash
   make setup
   # Edit .env with your TELEGRAM_BOT_TOKEN and CHAT_ID_WHITELIST
   ```

2. Run the bot:
   ```bash
   make run
   ```

## Development

```bash
# Run tests
make test

# Run with coverage
make test-cov

# Lint code
make lint

# Format code
make format
```

## Configuration

See `.env.example` for all available configuration options.

## License

MIT
