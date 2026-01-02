"""
Seed script to populate sample polls and options for testing.

Run with: uv run python -m app.scripts.seed_data
"""
import asyncio
from sqlalchemy import select
from app.db.core import async_session_factory, init_db
from app.models.poll import Poll
from app.models.option import Option


SAMPLE_POLLS = [
    {
        "question": "What is your favorite programming language?",
        "options": ["Python", "JavaScript", "Go", "Rust", "TypeScript"]
    },
    {
        "question": "Which cloud provider do you prefer?",
        "options": ["AWS", "Google Cloud", "Azure", "DigitalOcean", "Vercel"]
    },
    {
        "question": "What is the best backend framework?",
        "options": ["FastAPI", "Django", "Flask", "Express.js", "Spring Boot"]
    },
    {
        "question": "Which database do you use most often?",
        "options": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite"]
    },
    {
        "question": "What is your preferred code editor?",
        "options": ["VS Code", "Cursor", "Neovim", "JetBrains IDEs", "Sublime Text"]
    },
    {
        "question": "How do you prefer to deploy applications?",
        "options": ["Docker + Kubernetes", "Serverless", "VMs", "PaaS (Heroku/Render)", "Bare metal"]
    },
    {
        "question": "What's your favorite frontend framework?",
        "options": ["React", "Vue", "Svelte", "Angular", "HTMX"]
    },
]


async def seed_data():
    """Seed the database with sample polls and options."""
    # Initialize database tables
    # await init_db()
    
    async with async_session_factory() as session:
        # Check if data already exists
        existing_polls = await session.execute(select(Poll).limit(1))
        if existing_polls.scalar_one_or_none():
            print("⚠️  Data already exists. Skipping seed.")
            print("   To re-seed, clear the polls and options tables first.")
            return
        
        print("🌱 Seeding sample polls and options...")
        
        for poll_data in SAMPLE_POLLS:
            # Create poll
            poll = Poll(question=poll_data["question"])
            session.add(poll)
            await session.flush()  # Get the poll ID
            
            # Create options for this poll
            for option_text in poll_data["options"]:
                option = Option(text=option_text, poll_id=poll.id)
                session.add(option)
            
            print(f"   ✅ Created poll: {poll_data['question'][:50]}...")
        
        await session.commit()
        
        # Print summary
        from sqlalchemy import func
        poll_count = await session.scalar(select(func.count()).select_from(Poll))
        option_count = await session.scalar(select(func.count()).select_from(Option))
        
        print(f"\n🎉 Seeding complete!")
        print(f"   📊 Polls created: {poll_count}")
        print(f"   📝 Options created: {option_count}")


async def main():
    try:
        await seed_data()
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

