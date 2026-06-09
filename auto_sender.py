import asyncio
import logging
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat
from telethon.errors import FloodWaitError, ChatWriteForbiddenError, UserBannedInChannelError
import time
import random

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramUserbot:
    def __init__(self, api_id, api_hash, phone_number):
        """
        Initialize the userbot
        
        Args:
            api_id: Your Telegram API ID
            api_hash: Your Telegram API Hash  
            phone_number: Your phone number
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = TelegramClient('userbot_session', api_id, api_hash)
        
    async def start(self):
        """Start the client and authenticate"""
        await self.client.start(phone=self.phone_number)
        logger.info("Userbot started successfully!")
        
    async def get_all_groups(self):
        """
        Get all groups/channels the user has joined
        
        Returns:
            list: List of group entities
        """
        groups = []
        
        try:
            # Get all dialogs (chats, groups, channels)
            async for dialog in self.client.iter_dialogs():
                # Check if it's a group or channel
                if isinstance(dialog.entity, (Channel, Chat)):
                    # For channels, check if it's a supergroup or regular channel
                    if isinstance(dialog.entity, Channel):
                        if dialog.entity.megagroup or not dialog.entity.broadcast:
                            groups.append({
                                'entity': dialog.entity,
                                'title': dialog.title,
                                'id': dialog.entity.id,
                                'type': 'supergroup' if dialog.entity.megagroup else 'channel'
                            })
                    else:  # Regular group
                        groups.append({
                            'entity': dialog.entity,
                            'title': dialog.title,
                            'id': dialog.entity.id,
                            'type': 'group'
                        })
                        
            logger.info(f"Found {len(groups)} groups/channels")
            return groups
            
        except Exception as e:
            logger.error(f"Error getting groups: {e}")
            return []
    
    async def send_to_all_groups_once(self, message, exclude_ids=None):
        """
        Send message to all groups once (no delay between groups)
        
        Args:
            message: Message text to send
            exclude_ids: List of group IDs to exclude from sending
        """
        if exclude_ids is None:
            exclude_ids = []
            
        groups = await self.get_all_groups()
        
        if not groups:
            logger.warning("No groups found!")
            return 0, 0
            
        successful_sends = 0
        failed_sends = 0
        
        logger.info(f"🚀 Sending message to {len(groups)} groups...")
        
        for group in groups:
            try:
                # Skip if group is in exclude list
                if group['id'] in exclude_ids:
                    logger.info(f"⏭️ Skipping {group['title']} (excluded)")
                    continue
                
                # Send message
                await self.client.send_message(group['entity'], message)
                successful_sends += 1
                
                logger.info(f"✅ Message sent to: {group['title']} ({successful_sends}/{len(groups)})")
                    
            except FloodWaitError as e:
                logger.warning(f"⚠️ Flood wait for {e.seconds} seconds. Waiting...")
                await asyncio.sleep(e.seconds + 1)
                
                # Retry sending to current group
                try:
                    await self.client.send_message(group['entity'], message)
                    successful_sends += 1
                    logger.info(f"✅ Message sent to: {group['title']} (after flood wait)")
                except Exception as retry_error:
                    logger.error(f"❌ Failed to send to {group['title']} after retry: {retry_error}")
                    failed_sends += 1
                    
            except ChatWriteForbiddenError:
                logger.warning(f"❌ Cannot write to {group['title']} - No permission")
                failed_sends += 1
                
            except UserBannedInChannelError:
                logger.warning(f"❌ Banned in {group['title']}")
                failed_sends += 1
                
            except Exception as e:
                logger.error(f"❌ Error sending to {group['title']}: {e}")
                failed_sends += 1
        
        return successful_sends, failed_sends
    
    async def broadcast_with_delay(self, message, rounds=2, delay_between_rounds=10, exclude_ids=None):
        """
        Send message to all groups multiple times with delay between rounds
        
        Args:
            message: Message to send
            rounds: Number of times to send to all groups
            delay_between_rounds: Delay in seconds between each round
            exclude_ids: List of group IDs to exclude
        """
        total_success = 0
        total_failed = 0
        
        logger.info(f"🔥 Starting broadcast: {rounds} rounds with {delay_between_rounds} seconds delay")
        
        for round_num in range(1, rounds + 1):
            logger.info(f"\n🌟 === ROUND {round_num} of {rounds} ===")
            
            success, failed = await self.send_to_all_groups_once(message, exclude_ids)
            total_success += success
            total_failed += failed
            
            logger.info(f"📊 Round {round_num} Results: ✅ {success} success, ❌ {failed} failed")
            
            # Wait before next round (except after last round)
            if round_num < rounds:
                logger.info(f"⏱️ Waiting {delay_between_rounds} seconds before next round...")
                await asyncio.sleep(delay_between_rounds)
        
        logger.info(f"\n🎯 FINAL SUMMARY:")
        logger.info(f"✅ Total messages sent: {total_success}")
        logger.info(f"❌ Total failed: {total_failed}")
        logger.info(f"🔄 Rounds completed: {rounds}")
    
    async def list_groups(self):
        """List all joined groups with details"""
        groups = await self.get_all_groups()
        
        if not groups:
            logger.info("No groups found!")
            return
            
        logger.info(f"\n📋 Your Groups/Channels ({len(groups)} total):")
        logger.info("-" * 60)
        
        for i, group in enumerate(groups, 1):
            logger.info(f"{i}. {group['title']}")
            logger.info(f"   ID: {group['id']}")
            logger.info(f"   Type: {group['type']}")
            logger.info("-" * 60)
    
    async def stop(self):
        """Stop the client"""
        await self.client.disconnect()
        logger.info("Userbot stopped!")

def print_menu():
    """Print the user menu"""
    print("\n" + "="*60)
    print("📱 TELEGRAM USERBOT MENU")
    print("="*60)
    print("1. 📋 List all groups")
    print("2. 🚀 Send message to all groups (2 rounds, 10sec delay)")
    print("3. 📝 Send custom message")
    print("4. 🔄 Broadcast with custom rounds and delay")
    print("5. ❌ Exit")
    print("="*60)

async def main():
    # Your Telegram API credentials
    API_ID = 29237230  # Your API ID
    API_HASH = '04c8ff9738de961972a3ce478991b4ee'  # Your API Hash
    PHONE_NUMBER = '+919625273961'  # Your phone number
    
    # Initialize userbot
    bot = TelegramUserbot(API_ID, API_HASH, PHONE_NUMBER)
    
    try:
        # Start the userbot
        await bot.start()
        
        # Initial setup - show groups first
        print("\n" + "="*60)
        print("🔍 SCANNING YOUR GROUPS...")
        print("="*60)
        await bot.list_groups()
        
        # Interactive menu loop
        while True:
            print_menu()
            
            try:
                choice = input("\n👉 Enter your choice (1-5): ").strip()
                
                if choice == '1':
                    print("\n📋 Listing all groups...")
                    await bot.list_groups()
                
                elif choice == '2':
                    message = """
🤖 Hello from my userbot!

This is an automated message sent to all groups.
This will be sent 2 times with 10 seconds delay.

Best regards! 👋
"""
                    print("\n🚀 Starting broadcast (2 rounds, 10 sec delay)...")
                    await bot.broadcast_with_delay(
                        message=message,
                        rounds=2,
                        delay_between_rounds=10,
                        exclude_ids=[]
                    )
                
                elif choice == '3':
                    print("\n📝 Custom Message Sender")
                    print("-" * 30)
                    
                    custom_msg = input("Enter your custom message: ").strip()
                    if not custom_msg:
                        print("❌ Empty message! Please try again.")
                        continue
                    
                    rounds_input = input("Enter number of rounds (default: 1): ").strip()
                    rounds = int(rounds_input) if rounds_input.isdigit() else 1
                    
                    if rounds > 1:
                        delay_input = input("Enter delay between rounds in seconds (default: 10): ").strip()
                        delay = int(delay_input) if delay_input.isdigit() else 10
                    else:
                        delay = 0
                    
                    print(f"\n🚀 Sending custom message ({rounds} rounds)...")
                    await bot.broadcast_with_delay(
                        message=custom_msg,
                        rounds=rounds,
                        delay_between_rounds=delay,
                        exclude_ids=[]
                    )
                
                elif choice == '4':
                    print("\n🔄 Advanced Broadcast Settings")
                    print("-" * 30)
                    
                    message = input("Enter your message: ").strip()
                    if not message:
                        print("❌ Empty message! Please try again.")
                        continue
                    
                    rounds_input = input("Enter number of rounds: ").strip()
                    if not rounds_input.isdigit():
                        print("❌ Invalid number of rounds!")
                        continue
                    rounds = int(rounds_input)
                    
                    delay_input = input("Enter delay between rounds (seconds): ").strip()
                    if not delay_input.isdigit():
                        print("❌ Invalid delay time!")
                        continue
                    delay = int(delay_input)
                    
                    print(f"\n🚀 Starting broadcast ({rounds} rounds, {delay}s delay)...")
                    await bot.broadcast_with_delay(
                        message=message,
                        rounds=rounds,
                        delay_between_rounds=delay,
                        exclude_ids=[]
                    )
                
                elif choice == '5':
                    print("\n👋 Goodbye! Stopping userbot...")
                    break
                
                else:
                    print("❌ Invalid choice! Please enter 1-5.")
                
                # Wait before showing menu again
                input("\n⏸️ Press Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Program interrupted. Stopping userbot...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                input("⏸️ Press Enter to continue...")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    # Run the userbot
    asyncio.run(main())
