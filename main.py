# main.py

import asyncio
from database import init_db
from Customer_bot import build_customer_app
from staff_bot import build_staff_app


async def main():
    # Initialize the database (creates tables if they don't exist)
    await init_db()
    print("✅ Database ready.")

    # Build both bot applications
    customer_app = build_customer_app()
    staff_app    = build_staff_app()

    print("🤖 Starting Customer Bot and Staff Bot...")

    # Initialize both apps
    await customer_app.initialize()
    await staff_app.initialize()

    # Start polling for both bots
    await customer_app.updater.start_polling()
    await staff_app.updater.start_polling()

    await customer_app.start()
    await staff_app.start()

    print("✅ Both bots are running. Press Ctrl+C to stop.")

    # Keep running until Ctrl+C
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Stopping bots...")
    finally:
        await customer_app.updater.stop()
        await staff_app.updater.stop()
        await customer_app.stop()
        await staff_app.stop()
        await customer_app.shutdown()
        await staff_app.shutdown()
        print("✅ Bots stopped cleanly.")


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())