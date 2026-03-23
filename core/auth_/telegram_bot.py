import asyncio
import logging
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Service for handling Telegram bot interactions"""
    
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.application = None
        if self.token:
            self.bot = Bot(token=self.token)
        else:
            self.bot = None
    
    async def send_qr_login_message(self, chat_id: int, qr_code_url: str, session_code: str):
        """Send QR code login message to user"""
        if not self.bot:
            logger.error("Telegram bot not configured")
            return False
        
        try:
            message = (
                f"🔐 Login to OpenPage\n\n"
                f"Scan this QR code or click the button below to login:\n\n"
                f"Session Code: {session_code}\n\n"
                f"This link will expire in 5 minutes."
            )
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=message
            )
            
            # Send QR code as image if URL is provided
            if qr_code_url:
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=qr_code_url,
                    caption="QR Code for login"
                )
            
            return True
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    async def send_login_confirmation(self, chat_id: int):
        """Send login confirmation message"""
        if not self.bot:
            return False
        
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text="✅ You have successfully logged in to OpenPage!"
            )
            return True
        except Exception as e:
            logger.error(f"Error sending confirmation: {e}")
            return False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "👋 Welcome to OpenPage Bot!\n\n"
            "You can use this bot to login to your account.\n"
            "Go to the website and scan the QR code to login."
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        pass  # Can be extended for future features
    
    def setup_webhook(self, webhook_url: str):
        """Setup webhook for the bot"""
        if not self.token:
            logger.error("Cannot setup webhook: bot not configured")
            return False
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def _setup():
                await self.bot.set_webhook(webhook_url)
            
            loop.run_until_complete(_setup())
            logger.info(f"Webhook set to {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Error setting up webhook: {e}")
            return False
    
    def get_application(self):
        """Get the bot application instance"""
        if not self.token:
            return None
        
        if self.application is None:
            self.application = (
                Application.builder()
                .token(self.token)
                .build()
            )
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        return self.application


# Global bot instance
telegram_bot = TelegramBotService()
