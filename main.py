import asyncio
from aiohttp import web
from dotenv import load_dotenv
from instagram_api import verify_instagram_token, print_env_vars
from ai_handler import generate_ai_response
from reminder_bot import start_reminder_bot
import os
import sys
import logging
from webhook_handler import setup_routes
from message_handler import handle_message, process_pending_batches
import traceback

# Load environment variables
load_dotenv()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
INSTAGRAM_TOKEN = os.getenv("INSTAGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def setup_logging():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

logger = setup_logging()

async def process_batches_periodically():
    while True:
        await process_pending_batches()
        await asyncio.sleep(1)  # Check every second

async def main():
    logger.info("Starting the AI Consultant...")
    
    # Print all environment variables for debugging
    print_env_vars()

    if not all([VERIFY_TOKEN, INSTAGRAM_TOKEN, ANTHROPIC_API_KEY]):
        logger.error("One or more required environment variables are not set.")
        sys.exit(1)
    
    # Verify Instagram token
    logger.info("Verifying Instagram token...")
    if not await verify_instagram_token():
        logger.error("Instagram token is invalid or has expired. Please update the token in the .env file.")
        sys.exit(1)

    # Test AI response generation
    test_message = "Tell me about your programming course"
    test_user_id = "test_user_123"
    logger.info(f"Testing AI response generation with message: '{test_message}'")
    try:
        logger.debug("Calling handle_message function...")
        ai_response = await handle_message("Test", test_user_id, test_message)
        logger.info(f"AI response: {ai_response}")
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    
    # Start the reminder bot
    logger.info("Starting the reminder bot...")
    await start_reminder_bot()
    
    # Setup the server for Instagram webhook
    app = web.Application()
    setup_routes(app)

    # Start the server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    
    try:
        await site.start()
        logger.info("Server started on port 8080")
        
        # Start the batch processing coroutine
        batch_processing_task = asyncio.create_task(process_batches_periodically())
        
        # Run the server indefinitely
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        if 'batch_processing_task' in locals():
            batch_processing_task.cancel()
            try:
                await batch_processing_task
            except asyncio.CancelledError:
                pass
        await runner.cleanup()
        logger.info("Server closed")

if __name__ == "__main__":
    asyncio.run(main())