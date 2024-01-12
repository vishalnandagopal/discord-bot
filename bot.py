from os import getenv, listdir, environ
from os.path import dirname

import discord
from distutils.command.check import check
import requests
from discord.ext import commands
from dotenv import load_dotenv
from firebase_admin import credentials, db, initialize_app

# Read environment variables set at ./.env
if not load_dotenv(f"{dirname(__file__)}/.env"):
    raise RuntimeError(
        f"Could not load env file. Make sure it is located at {dirname(__file__)}/.env"
    )


debug = getenv("DEBUG") in {"TRUE", "true", "True"}
print(f"DEBUG={debug}")


def check_if_required_env_variables_are_present():
    required_env_variables = {
        "CURRENT_ACT",
        "FIREBASE_DB",
        "FIREBASE_STORAGE",
        "BOT_TOKEN",
    }
    if not all(env in environ for env in required_env_variables):
        raise RuntimeError(
            f"The following required environmental variables have not been set - {(x for x in required_env_variables if x not in environ)}"
        )


check_if_required_env_variables_are_present()


# Initialize Firebase app
creds = credentials.Certificate("firebase.json")
initialize_app(
    creds,
    {
        "databaseURL": getenv("FIREBASE_DB"),
        "storageBucket": getenv("FIREBASE_STORAGE"),
    },
)

current_act = getenv("CURRENT_ACT") if getenv("CURRENT_ACT") else 6
"""The current leaderboard act"""


leaderboard_ref = db.reference("vitcc").child("owasp").child(current_act)

# project_ref = base_ref.child("projects")
# certificate_ref = base_ref.child("certificates")
# ctf_ref = base_ref.child("ctf")


spam_bait_channel_id = getenv("SPAM_BAIT_CHANNEL_ID")
spam_log_channel_id = getenv("SPAM_LOG_CHANNEL_ID")

command_prefix = "!cyscom" if not debug else "!cyscom-dev"

bot = commands.Bot(
    command_prefix=f"{command_prefix} ",
    description="The official CYSCOM VITCC Discord Bot.",
    activity=discord.Game(name="CYSCOM Leaderboard"),
    intents=discord.Intents.all(),
)


cyscom_logo_url = "https://cyscomvit.com/assets/images/logo.png"


def embed_generator(
    ctx, description: str, name: str, rating: int = 0, contributions: int = 0
):
    """Returns a usable discord embed"""

    embed = discord.Embed(
        title=f"{ctx.guild.name}",
        description=description,
        color=discord.Color.blue(),
    )

    embed.add_field(name="Name", value=name)
    embed.add_field(name="Rating", value=rating)
    embed.add_field(name="Contributions", value=contributions)

    embed.set_thumbnail(url=cyscom_logo_url)

    return embed


@bot.command()
async def ping(ctx):
    """Check to see if bot is working. Also returns path of the script"""
    msg = f"pong from bot running at {dirname(__file__)}"
    print(msg)
    await ctx.send(msg)


@bot.command()
async def doge(ctx):
    """Return a doge pic"""
    try:
        doge_pic_url = requests.get(
            "https://shibe.online/api/shibes?count=1&urls=true"
        ).json()[0]
        await ctx.send(doge_pic_url)

    except Exception as e:
        print(e)
        ctx.send(str(e))


@bot.command()
async def sum(ctx, numOne: int, numTwo: int):
    f"""Return a sum of 2 numbers. {command_prefix} sum num1 num2"""
    await ctx.send(numOne + numTwo)


@bot.command()
@commands.has_any_role("Board Member")
async def add_data(ctx, name: str, rating: int = 0, contributions: int = 0):
    f"""Add data to the leaderboard. Call it by {command_prefix} add_data "name" rating contribution"""
    try:
        data = leaderboard_ref.get()
        name = name.strip()

        if not name:
            ctx.send("No name given")
            return None

        if data != None:
            for key, value in data.items():
                if value["Name"].casefold() == name.casefold():
                    embed = embed_generator(
                        ctx,
                        "User already exists",
                        name,
                        value["Rating"],
                        value["Contributions"],
                    )

                    await ctx.send(embed=embed)
                    return None

        # Insert name since it does not exist on the firebase server
        leaderboard_ref.push(
            {
                "Name": name,
                "Rating": int(rating),
                "Contributions": int(contributions),
            }
        )

        embed = embed_generator(
            ctx,
            "Added data to the CYSCOM Leaderboard.",
            name,
            rating,
            contributions,
        )

        print(f"Added {name}")

        await ctx.send(embed=embed)

    except Exception as e:
        print(e)


@bot.command()
@commands.has_any_role("Board Member")
async def add_recruits(ctx):
    f"""Add recruits by reading a members.txt file present in the same folder"""
    # Place file in discord-bot folder.
    try:
        filename = "members.txt"
        if filename not in listdir(dirname(__file__)):
            await ctx.send(f"File {filename} not found in {dirname(__file__)}")
            return None
        else:
            with open(filename, "r") as f:
                members = f.read().split("\n")
                print(members)
            if members[0].casefold() == "name":
                ctx.send(
                    f"Members file ({filename}) is supposed to only have 1 name on each line, and must have no headers!"
                )
                return None

        for name in members:
            await add_data(ctx, name)

    except Exception as e:
        print(e)


@bot.command()
@commands.has_any_role("Board Member")
async def update_data(ctx, name: str, rating=0, contributions=0):
    try:
        data = leaderboard_ref.get()
        name = name.strip()

        if not name:
            ctx.send("No name given")
            return None

        if data != None:
            for key, value in data.items():
                if value["Name"].casefold() == name.casefold():
                    selector = leaderboard_ref.child(key)
                    selector.update(
                        {
                            "Name": name,
                            "Rating": int(rating),
                            "Contributions": int(contributions),
                        }
                    )

                    embed = embed_generator(
                        ctx,
                        "Updated data on the CYSCOM Leaderboard.",
                        name,
                        rating,
                        contributions,
                    )

                    print(f"Updated {name}")

                    await ctx.send(embed=embed)

    except Exception as e:
        print(e)


@bot.command()
@commands.has_any_role("Member", "Board Member")
async def fetch_data(ctx, name):
    """Fetch data from the leaderboard"""
    try:
        data = leaderboard_ref.get()
        if data != None:
            for key, value in data.items():
                if value["Name"].casefold() == name.casefold():
                    embed = embed_generator(
                        ctx,
                        "Fetched CYSCOM Leaderboard profile.",
                        name,
                        value["Rating"],
                        value["Contributions"],
                    )

                    await ctx.send(embed=embed)
    except Exception as e:
        print(e)


@bot.command()
@commands.has_any_role("Board Member")
async def delete_data(ctx, name):
    """Delete someone from the leaderboard"""
    try:
        data = leaderboard_ref.get()
        if data != None:
            for key, value in data.items():
                if value["Name"].casefold() == name.casefold():
                    leaderboard_ref.child(key).set({})
                    embed = embed_generator(
                        ctx, "Deleted data from the Leaderboard", name
                    )
                    await ctx.send(embed=embed)
    except Exception as e:
        print(e)


@bot.command()
@commands.has_any_role("Leaderboard", "Board Member")
async def contribution(ctx, name, task):
    """Add contribution to a member"""
    try:
        data = leaderboard_ref.get()
        if data != None:
            for key, value in data.items():
                if value["Name"].casefold() == name.casefold():
                    selector = leaderboard_ref.child(key)

                    points_dict = {
                        "pull request": 20,
                        "blog medium": 20,
                        "blog": 15,
                        "sm posting": 7,
                        "weekly work": 5,
                        "idea": 3,
                        "brochure": 10,
                        "news": 5,
                        "demos": 20,
                        "oc volunteer": 30,
                        "oc assigned": 20,
                        "oc no work": 10,
                        "oc manager": 50,
                        "wtf": 50,
                        "discord": 10,
                        "marketing": 20,
                        "mini project": 100,
                        "complete project": 200,
                        "promotion medium": 25,
                        "promotion large": 50,
                    }

                    rating = selector["Rating"] + points_dict[task.casefold()]
                    contributions = selector["Contributions"] + 1

                    selector.update(
                        {
                            "Rating": int(rating),
                            "Name": name,
                            "Contributions": int(contributions),
                        }
                    )

                    embed = embed_generator(
                        ctx,
                        "Added contribution to the CYSCOM Leaderboard.",
                        name,
                        rating,
                        contributions,
                    )

                    await ctx.send(embed=embed)
                    return None

        await ctx.send("Name not present")

    except Exception as e:
        print(e)


@bot.command()
@commands.has_any_role("Member", "Cabinet Member")
async def attendance(ctx, channel_name):
    f"""Mark attendance in a voice channel. Call by {command_prefix} attendance voice_channel_name"""

    # Get the voice channel by name
    channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)

    if channel:
        # Fetch all the members in the specified voice channel
        members = channel.members
        message = f"```Members in channel {channel.name} - {channel.id}\n\n"
        if members:
            message += f"There are {len(members)} member(s)\n\n"
            # Print member names and IDs
            for i, member in enumerate(members):
                message += f"{i+1} - {member.name} - {member.id}\n"

        else:
            message += "There are no members in this voice channel.\n"
        message += "```"
        await ctx.send(message)
    else:
        await ctx.send("Voice channel not found.")


# Events
@bot.event
async def on_ready():
    """Message to be sent when bot is ready"""
    print("CYSCOM VITCC Bot v1.0")


@bot.listen()
async def on_message(message):
    """Run every message in the server through this function to check for spam, whether someone is asking github link etc"""
    if message.channel.id == spam_bait_channel_id:
        ctx = bot.get_channel(spam_log_channel_id)
        try:
            await message.author.ban()
        except:
            await ctx.send(
                f"USER cannot be banned due to permission issue User-<@{message.author.id}> \nmessage-{message.content}"
            )
            return

        embed = discord.Embed(
            title=f"{ctx.guild.name}",
            description="Banned for typing in #SPAM_BAIT.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Name", value=f"{message.author.id}")
        embed.add_field(name="Message", value=f"{message.content}")
        embed.set_thumbnail(url=cyscom_logo_url)
        await ctx.send(embed=embed)
        return

    elif "cyscom github" in message.content.lower():
        await message.channel.send("Our GitHub is https://github.com/cyscomvit")
        await bot.process_commands(message)

    elif "cyscom website" in message.content.lower():
        await message.channel.send("Our Website is https://cyscomvit.com")
        await bot.process_commands(message)


bot.run(getenv("BOT_TOKEN"))