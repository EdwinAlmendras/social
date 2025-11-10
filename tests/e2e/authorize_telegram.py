"""Script para autorizar la sesión de Telegram para los tests E2E."""
import asyncio
import os
from pathlib import Path
from telethon import TelegramClient
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


async def authorize_session():
    """Autoriza la sesión de Telegram."""
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    print("🔐 Telegram Session Authorization")
    print("=" * 50)
    print(f"API ID: {api_id}")
    print(f"API Hash: {api_hash[:10]}...")
    print()
    
    # Usar la misma sesión que los tests
    session_file = 'uploader'
    session_path = Path(f'{session_file}.session')
    
    print(f"📁 Session file: {session_path.absolute()}")
    print(f"   Exists: {session_path.exists()}")
    print()
    
    client = TelegramClient(session_file, api_id, api_hash)
    
    print("🔌 Connecting to Telegram...")
    await client.connect()
    
    if await client.is_user_authorized():
        print("✅ Already authorized!")
        me = await client.get_me()
        print(f"   User: {me.first_name} {me.last_name or ''}")
        print(f"   Phone: {me.phone}")
        print(f"   ID: {me.id}")
    else:
        print("❌ Not authorized. Starting authorization process...")
        print()
        
        # Solicitar número de teléfono
        phone = input("📱 Enter your phone number (with country code, e.g., +1234567890): ")
        
        await client.send_code_request(phone)
        print("📨 Code sent to your Telegram app!")
        
        # Solicitar código
        code = input("🔢 Enter the code you received: ")
        
        try:
            await client.sign_in(phone, code)
            print("✅ Successfully authorized!")
            
            me = await client.get_me()
            print(f"   User: {me.first_name} {me.last_name or ''}")
            print(f"   Phone: {me.phone}")
            print(f"   ID: {me.id}")
            
        except Exception as e:
            print(f"❌ Authorization failed: {e}")
            
            # Si requiere contraseña de dos factores
            if "password" in str(e).lower():
                password = input("🔐 Enter your 2FA password: ")
                await client.sign_in(password=password)
                print("✅ Successfully authorized with 2FA!")
    
    print()
    print("=" * 50)
    print("✅ Session is ready for E2E tests!")
    print(f"   Session file: {session_path.absolute()}")
    
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(authorize_session())
