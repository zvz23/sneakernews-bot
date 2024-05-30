from discord.ext import tasks, commands
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import asyncio
import discord
import asyncio
import parsel
import os

load_dotenv(override=True)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

Sneaker_Home_URL = 'http://sneakernews.com'
Sneaker_realeases = "https://sneakernews.com/air-jordan-release-dates/"
DEFAULT_THUMBNAIL = "https://sneakernews.com/wp-content/themes/sneakernews-redesign/images/mobile-header-logo-white.png"

SNEAKERS_CHANNEL = "1242902553541349396"

intents = discord.Intents.default()  # Create a new Intents object
intents.message_content = True  # Enable the guild_members intent
bot = commands.Bot(command_prefix='!', intents=intents)  # Pass the Intents object to the Bot constructor

@tasks.loop(seconds=3600)  # Scrape every hour
async def get_and_send_sneaker_releases(ctx):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(Sneaker_realeases)
        await page.wait_for_timeout(5000)  # Wait for 5 seconds for the page to load
        # Get the URLs of the releases
        sneaker_container_sels = await page.query_selector_all("div.releases-box")
        sneakers = []
        for sel in sneaker_container_sels:
            sneaker = {}
            sneaker_a_tag = await sel.query_selector("a.prod-name")
            sneaker["url"] = await sneaker_a_tag.evaluate("node => node.href")
            sneaker["name"] = await sneaker_a_tag.inner_text()
            sneaker["image_url"] = await sel.eval_on_selector("img", "node => node.src")
            sneaker["retail_price"] = (await sel.eval_on_selector("p.release-price", "node => node.innerText")).split(":")[-1].strip()
            sel_html = await sel.evaluate("node => node.outerHTML")
            selector = parsel.Selector(text=sel_html)
            sneaker["size_run"] = selector.xpath(".//span[contains(text(), 'Size Run:')]/../text()").getall()[-1].strip()
            sneaker["color"] = selector.xpath(".//span[contains(text(), 'Color:')]/../text()").getall()[-1].strip()
            sneaker["style_code"] = selector.xpath(".//span[contains(text(), 'Style Code:')]/../text()").getall()[-1].strip()
            sneaker["region"] = selector.xpath(".//span[contains(text(), 'Region:')]/../text()").getall()[-1].strip()
            sneakers.append(sneaker)
        await browser.close()

        # Pair each release URL with its corresponding image URL and sneaker name
        for sneaker in sneakers:
            embed=discord.Embed(title=sneaker["name"].strip(), url=sneaker["url"], color=0xFF5733)
            embed.set_image(url=sneaker["image_url"])
            embed.set_thumbnail(url=DEFAULT_THUMBNAIL)
            embed.add_field(name="Retail Price", value=sneaker["retail_price"], inline=True)
            embed.add_field(name="Size Run", value=sneaker["size_run"], inline=True)
            embed.add_field(name="Color", value=sneaker["color"], inline=False)
            embed.add_field(name="Style Code", value=sneaker["style_code"], inline=True)
            embed.add_field(name="Region", value=sneaker["region"], inline=False)

            await ctx.channel.send(embed=embed)

@bot.command()
async def start_releases_monitor(ctx):
    if get_and_send_sneaker_releases.is_running():
        await ctx.channel.send("It's already running you dumbass")
        return
    await ctx.channel.send("Started.")
    get_and_send_sneaker_releases.start(ctx)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

async def stop_releases_monitor(ctx):
    if get_and_send_sneaker_releases.is_running():
        get_and_send_sneaker_releases.stop()
    await ctx.send("Sneaker releases monitoring stopped.")


bot.run(BOT_TOKEN)






