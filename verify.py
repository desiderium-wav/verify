import discord
from discord.ext import commands
import pytesseract
import cv2
from deepface import DeepFace
from PIL import Image
import requests
import os
from io import BytesIO
import re

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ROLE_NAME = "Verified 18+"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def verify(ctx):
    await ctx.send("📸 **Step 1**: Upload your **Photo ID** clearly showing your date of birth.")

    def check(m):
        return m.author == ctx.author and len(m.attachments) > 0

    try:
        id_msg = await bot.wait_for('message', check=check, timeout=180)
        id_img = Image.open(BytesIO(requests.get(id_msg.attachments[0].url).content))
        id_img.save("id.jpg")

        # OCR to extract DOB
        text = pytesseract.image_to_string(cv2.imread("id.jpg"))
        dob = extract_dob_from_text(text)

        if dob is None:
            await ctx.send("❌ Could not detect DOB. Please retry.")
            os.remove("id.jpg")
            return

        await ctx.send(f"✅ DOB detected: {dob}\n\n📸 **Step 2**: Upload a **selfie** clearly showing your face.")

        selfie_msg = await bot.wait_for('message', check=check, timeout=180)
        selfie_img = Image.open(BytesIO(requests.get(selfie_msg.attachments[0].url).content))
        selfie_img.save("selfie.jpg")

        await ctx.send("🔄 Verifying identity...")

        # Facial recognition check
        result = DeepFace.verify("selfie.jpg", "id.jpg", enforce_detection=False)

        if result["verified"]:
            role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME)
            if role is None:
                role = await ctx.guild.create_role(name=ROLE_NAME)
            await ctx.author.add_roles(role)
            await ctx.send("✅ Identity verified. Access granted!")
        else:
            await ctx.send("❌ Facial verification failed. Try again.")

    except Exception as e:
        await ctx.send(f"⚠️ Verification error: {str(e)}")

    finally:
        cleanup(["id.jpg", "selfie.jpg"])

def extract_dob_from_text(text):
    match = re.search(r"(\d{2}[\/\-]\d{2}[\/\-]\d{4})", text)
    return match.group(1) if match else None

def cleanup(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)

bot.run(TOKEN)
