# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-06-XX

### Changed

- Updated README for accuracy and clarity, reflecting actual project structure and features.

### Known Issues

- SMS messages may sometimes be flagged by the carrier as 'Short code', making it impossible for recipients to reply to the SMS.

## [0.1.0] - 2025-01-19

### Added

- Initial development release of the Order Confirmation Agent prototype
- FastAPI backend with comprehensive REST API
- LLM-powered conversation agent with multilingual support (French/English)
- SQLite database for order and conversation storage
- Web interface for order management and testing
- Address confirmation workflow
- Order modification capabilities (add, remove, replace items)
- Language detection and response generation
- Conversation state management
- Comprehensive error handling and fallback mechanisms

### Features

- **Order Management**: Create, read, update, delete orders
- **Conversation Agent**: Intelligent order confirmation with LLM
- **Multilingual Support**: French and English language detection and responses
- **Address Collection**: Mandatory delivery address confirmation workflow
- **Order Modifications**: Add, remove, replace items during confirmation
- **Web Interface**: User-friendly interface for testing and management
- **API Endpoints**: Complete REST API for integration

### Technical Details

- Built with FastAPI and Python 3.11+
- Uses Google Generative AI for LLM capabilities
- SQLite database with SQLAlchemy ORM
- Pydantic models for data validation
- Comprehensive test suite
- Production-ready error handling

### Fixed

- Duplicate address confirmation prompts
- LLM interference with address collection workflow
- Null reference issues in conversation handling
- Type safety improvements

### Known Issues

- Still in development/prototype phase
- Not ready for production deployment
- Limited error handling for edge cases
- No authentication/authorization system
- No rate limiting or security hardening

### Security

- Input validation and sanitization
- SQL injection prevention
- Error message sanitization
