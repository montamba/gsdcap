import asyncio
from dotenv import load_dotenv
from vercel import blob


load_dotenv()
 

async def main() -> None:
    uploaded = await blob.put_blob(
        "reports/summary.txt",
        b"Quarterly summary",
        access="private",  # or "public"
        add_random_suffix=True,
    )
    print(uploaded.url)
 
 
asyncio.run(main())