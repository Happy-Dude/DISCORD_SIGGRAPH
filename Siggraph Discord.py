import discord
import pandas as pd
from discord.ext import commands
import datetime as dt
import pickle
import os.path
import logging

import constants

# https://stackoverflow.com/a/44401529
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Resource: https://realpython.com/how-to-make-a-discord-bot-python/
TOKEN = constants.TEST_TOKEN  # test server

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

messages_to_monitor = []
message_pickle = 'messages_test.pickle'  # Test server


# message_pickle = 'messages_production.pickle'  #prod server


@bot.event
async def on_ready():
    logger.info(f"{bot.user.name} has connected to Discord!")
    logger.info(f"Logged on as {bot.user.name}!")
    if (os.path.exists(message_pickle)):
        with open(message_pickle, 'rb') as f:
            global messages_to_monitor
            messages_to_monitor = pickle.load(f)
    for guild in bot.guilds:
        logger.info(f"Server: {guild.name}, Id: {guild.id}")


@bot.command(name='create_channel', description='Create text channel Channel here', brief="Let There be Channels")
async def create_channel(ctx, *args):
    if (not await checkRole(ctx)):
        return
    if len(args) > 0:
        for arg in args:
            await bot.guilds[0].create_text_channel(arg)
            await ctx.send('Created Channel named {}'.format(arg))
    else:
        await bot.guilds[0].create_text_channel("Empty Channel")


@bot.command(name='ping', description='The Classic Ping Pong example', brief='PING PONG')
async def ping(ctx):
    await ctx.send('Pong!')


# PRINT OUT EXISTING CHANNELS

# DELETES all the channels in the system

# we might need to be careful about which server we delete the channels and specify the ID


@bot.command(name='purge', description='delete every channel here in this system', brief='DELETE EVERYTHING')
async def purge(ctx):
    if (not await checkRole(ctx)):
        return
    our_guild = ctx.guild
    channels_in_guild = await our_guild.fetch_channels()
    if len(channels_in_guild) > 0:
        for channel in channels_in_guild:
            logger.info(channel.name)
            if ("welcome-page" in channel.name):
                logger.info("Skipping Welcome Page")
            else:
                await channel.delete()
    await ctx.send('All channels and categories are gone!!!')


# Read from CSV


@bot.command(name='create_from_CSV', description='create channels and categories from CSV',
             brief='starts the new world ')
async def createFromCSV(ctx):
    if (not await checkRole(ctx)):
        return
    session_file = "..\s2021_sessions_7_16.csv"  # prod csv
    # session_file = "..\s2021_sessions_2021_6_24 - s2021_sessions_2021_6_24.csv" #test csv
    df = pd.read_csv(session_file)
    categories = {}
    for event_type in df["Category"].unique():
        if isinstance(event_type, str):
            category = await bot.guilds[0].create_category(event_type)
            categories[event_type] = category
    await ctx.send('created all the categories!')

    df["Reduced_sessionTitle"] = df['Session Title'].str.strip().str[:100]
    # This Format : https://discord.com/channels/779464282878115880/854343504058384424
    df["Channel Link"] = ""
    for index, row in df.iterrows():
        # We can't have more than 50 channels in category
        topic_to_set = ""
        if (pd.isnull(row["Hubb Link"])):
            if not pd.isnull(row["Topic"]):
                topic_to_set = str(row["Topic"])
            else:
                topic_to_set = "No Specific Topic set"
        else:
            topic_to_set = str(row["Topic"]) + "\n"  # +str(row["Hubb Link"])

        if (not isinstance(row['Category'], str)) or (len(categories[row['Category']].channels) < 50):
            # TODO: check for empty categories
            channel_id = 0

            if (row["Type of Channel"] == 'Text') or (pd.isnull(row["Type of Channel"])):
                if not (pd.isnull(row["Category"])):
                    channel = await bot.guilds[0].create_text_channel(row['Reduced_sessionTitle'],
                                                                      category=categories[row['Category']],
                                                                      topic=topic_to_set)
                else:
                    channel = await bot.guilds[0].create_text_channel(row['Reduced_sessionTitle'], topic=topic_to_set)
                botmsg = await channel.send(topic_to_set)
                await botmsg.pin()
            elif row["Type of Channel"] == 'Voice':
                if isinstance(row['Category'], str):
                    channel = await bot.guilds[0].create_voice_channel(row['Reduced_sessionTitle'],
                                                                       category=categories[row['Category']])
                else:
                    channel = await bot.guilds[0].create_voice_channel(row['Reduced_sessionTitle'])
            elif row["Type of Channel"] == 'Stage':
                # Stage channels are only available to community servers
                if isinstance(row['Category'], str):
                    channel = await bot.guilds[0].create_text_channel(row['Reduced_sessionTitle'],
                                                                      category=categories[row['Category']],
                                                                      topic=topic_to_set)
                else:
                    channel = await bot.guilds[0].create_text_channel(row['Reduced_sessionTitle'], topic=topic_to_set)

            channel_id = channel.id
            row["Channel Link"] = "https://discord.com/channels/{0}/{1}".format(
                ctx.guild.id, channel_id)
    df.to_csv(session_file, index=False)
    await ctx.send('All channels and categories are created from CSV!!!')


@bot.command(name='create_links', description='create links for all the participants ex:\'!create_links 10 \' ',
             brief='create invite links ')
async def createInviteLinks(ctx, *args):
    if (not await checkRole(ctx)):
        return
    email_csv = "..\Invitation_links.csv"
    emails = pd.DataFrame(columns=['Numbers', 'Invitation links'])
    our_guild = ctx.guild
    logger.info(our_guild)
    number_of_links = 10
    channel_to_use = 0
    if ((len(args) > 0) and args[0].isdigit()):
        logger.info(args[0])
        number_of_links = int(args[0])
    if ((len(args) > 1) and args[1].isdigit()):
        logger.info(args[1])
        channel_to_use = int(args[1])

    emails["Numbers"] = pd.Series(range(1, number_of_links + 1))
    emails["Invitation links"] = ""
    # TODO use args to parse number of emails

    # TODO: set the expiration time for the link to. This is set in seconds for max_age.
    # They need to expire on October 29,2021 (10/29/2021). Max age we can set is 604800 which is 7 days.
    # No expiration set
    seconds_to_expire = int((
                                    dt.datetime(year=2021, month=10, day=29) - dt.datetime.now()).total_seconds())
    logger.info(f"Links will expire in {seconds_to_expire} seconds.")
    logger.info(our_guild.channels)
    for index, row in emails.iterrows():
        logger.info(row['Numbers'])
        # Expiration should be never
        # Reference: https://discordpy.readthedocs.io/en/latest/api.html?highlight=create_invite#discord.abc.GuildChannel.create_invite
        # ASSUMPTION: The link should not expire but is allowed to be used only once . <-- THis changed and now we have 11 uses per link
        # Email is not needed
        logger.info(our_guild.channels[channel_to_use])
        invite = await our_guild.channels[channel_to_use].create_invite(max_age=0, max_uses=11)

        emails.at[index, "Invitation links"] = invite.url
        logger.info(invite.url)
    emails.to_csv(email_csv, index=False)
    await ctx.send('Invitation links were created!')


@bot.command(name='reset', description='delete everything and create again from a csv', brief='restart the world')
async def resetWorld(ctx):
    if (not await checkRole(ctx)):
        return
    await purge(ctx)
    await createFromCSV(ctx)


@bot.command(name='members', description='Gets you the members in the guild', brief='Who is in the server')
async def getMembers(ctx):
    if (not await checkRole(ctx)):
        return
    our_guild = ctx.guild
    # There are 16 members
    logger.info(f"How many members are in this server {our_guild.member_count}")
    # logger.info(our_guild.members)
    # members = our_guild.fetch_members()
    members = our_guild.members
    logger.info(f"The length of members from the call {len(members)}")
    df = pd.DataFrame(
        columns=('Name', 'Discriminator', 'ID', 'Display Name', 'Status', "Joined on"))
    i = 0
    for member in members:
        logger.info(
            f"{member.name}, {member.discriminator}, {member.id}, {member.display_name}, {member.status}, {member.joined_at}")
        df.loc[i] = [member.name, member.discriminator, member.id,
                     member.display_name, member.status, member.joined_at]
        i = i + 1
        # logger.info(member.roles)
    df.to_csv("..\Members from {}.csv".format(our_guild.name), index=False)
    await ctx.send('Retrieved all members')


# TODO: find a way to reset roles if need be
# await remove_roles(*roles, reason=None, atomic=True)


@bot.command(name='assign_roles', description='Assign the roles to the different members', brief='Tell who does what')
async def roleAssigned(ctx):
    if (not await checkRole(ctx)):
        return
    df = pd.read_csv("..\Role Assignment.csv")
    df[["Name", "delim"]] = df["User name"].str.split("#", expand=True)
    our_guild = ctx.guild
    # logger.info(our_guild.roles)
    for index, row in df.iterrows():
        role = discord.utils.get(our_guild.roles, name=row["Role"])
        member = discord.utils.get(
            our_guild.members, name=row["Name"], discriminator=str(row["delim"]))
        await member.add_roles(role)
    # discord.Member. add_roles

    await ctx.send('the roles have been assigned')


@bot.command(name='export_channels', description='export channel links, names, and categories to server',
             brief='export channel links to csv')
async def exportChannels(ctx):
    if (not await checkRole(ctx)):
        return
    our_guild = ctx.guild
    channels_in_guild = await our_guild.fetch_channels()
    df = pd.DataFrame(columns=('Channel Name', 'Category', 'Type', 'link'))
    if len(channels_in_guild) > 0:
        for i, channel in enumerate(channels_in_guild):
            logger.info(f"{channel.name}, {channel.category}, {channel.type}, {channel.id}")
            link = "https://discord.com/channels/{0}/{1}".format(
                our_guild.id, channel.id)
            df.loc[i] = [channel.name, channel.category, channel.type, link]

    await ctx.send('All channels links have been found!')
    df.to_csv("..\Channel info from {}.csv".format(
        our_guild.name), index=False)
    await ctx.send("dumped to 'Channel info from {}.csv'".format(our_guild.name))


@bot.command(name='help_moderator', description='Send help to the support channel',
             brief='ask for help in the support channel')
async def askForHelp(ctx, args):
    our_guild = ctx.guild
    support_channel = discord.utils.get(
        our_guild.channels, name="moderators-hidden")
    await support_channel.send(f"Hello support {ctx.message.author} said: {args}")
    await ctx.send("Your message was forwarded to support")


@bot.command(name='send_all', description='send Message to all channels', brief='megaphone to everyone')
async def sendAll(ctx, args):
    our_guild = ctx.guild
    members = our_guild.members
    role_needed = discord.utils.get(our_guild.roles, name="SIGGRAPH_Chair")
    member_in_question = discord.utils.get(
        our_guild.members, name=ctx.message.author.name)
    if (role_needed in member_in_question.roles):
        await ctx.send(f"You do have the permissions to send {args}")
        for channel in our_guild.text_channels:
            await channel.send(f"Announcement: {args}")
        await ctx.send("Message has been sent to everyone")
    else:
        await ctx.send("You do have permissions to use this command")


# !send_message channel "the message to send"


@bot.command(name='send_message', description="Updates the guidelines message", brief='Guidelines message')
async def updateGuideline(ctx, *args):
    our_guild = ctx.guild
    channel = discord.utils.get(
        our_guild.channels, name=args[0])
    await channel.send(args[1])


# !send_to_category "the message to send" category


@bot.command(name='send_to_category', description="send Message to all channels in category example:" +
                                                  " '!send_to_category \"the message to send\" category' ",
             brief='megaphone to category')
async def sendToAll(ctx, *args):
    our_guild = ctx.guild
    members = our_guild.members
    role_needed = discord.utils.get(our_guild.roles, name="SIGGRAPH_Chair")
    member_in_question = discord.utils.get(
        our_guild.members, name=ctx.message.author.name)
    if (role_needed in member_in_question.roles):
        await ctx.send(f"You do have the permissions to send {args[0]}")
        await ctx.send(f"{args[0]}")
        await ctx.send(f"{args[1]}")
        for category_asked in args[1:]:
            # if our_guild.categories.exists('name', category_asked):
            category_announce = discord.utils.get(
                our_guild.categories, name=category_asked)
            if category_announce is not None:
                for channel in category_announce.channels:
                    await channel.send(f"Announcement: {args[0]}")
                await ctx.send(f"Message has been sent to channels in {category_asked}")
            else:
                ctx.send(f"{category_asked} is not a valid category")
    else:
        await ctx.send("You do have permissions to use this command")


@bot.command(name='send_role_messages', description="send the role messages from the csv to assign roles",
             brief='messages to help assign roles')
async def sendRoleMessages(ctx):
    if (not await checkRole(ctx)):
        return
    our_guild = ctx.guild
    df = pd.read_csv("..\Channels, Categories, and Roles - Roles.csv")
    emoji_data = pd.read_excel("..\Emoji Data.xlsx")

    welcome_channel = discord.utils.get(
        our_guild.channels, name="welcome-page")
    global messages_to_monitor
    messages_to_monitor = []
    for column in df.columns:
        message = ""
        # message += column+" Roles \n"
        df_temp = df[column]
        emojis = []
        for i in range(len(df_temp)):
            if not pd.isnull(df_temp.iloc[i]):
                words_roles = df_temp.iloc[i].split(':')[:2]
                if len(words_roles) > 1:
                    emojis.append(":" + words_roles[1] + ":")
                    message += words_roles[0] + ":" + words_roles[1] + ":" + "\n"
                else:
                    message += df_temp.iloc[i] + "\n"

        # TODO: add bot reactions to message. Need to have an automated way to find emoji ID. So the bot can react to message
        message_sent = await welcome_channel.send(message)
        messages_to_monitor.append(message_sent.id)
        for emoji_str in emojis:
            # We need to make sure if emoji in list if not we can add it.
            emoji_symbol = emoji_data.loc[emoji_data['Shortcode']
                                          == emoji_str, 'Symbol'].values[0]
            if emoji_symbol:
                await message_sent.add_reaction(emoji_symbol)

            role = emoji_data.loc[emoji_data['Shortcode']
                                  == emoji_str, 'Role'].values[0]
            if role:
                await createRole(ctx, role, messages=False)
    global message_pickle
    with open(message_pickle, 'wb') as f:
        pickle.dump(messages_to_monitor, f)
    await ctx.send("Sent the role messages")


@bot.command(name='edit_role_messages', description="edit the role messages that were already sent",
             brief='edit the message to help assign roles')
async def editRoleMessages(ctx):
    if (not await checkRole(ctx)):
        return
    our_guild = ctx.guild
    welcome_channel = discord.utils.get(
        our_guild.channels, name="welcome-page")
    df = pd.read_csv("..\Channels, Categories, and Roles - Roles.csv")
    emoji_data = pd.read_excel("..\Emoji Data.xlsx")

    for column in df.columns:
        message_tosend = ""
        df_temp = df[column]
        emojis = []
        for i in range(len(df_temp)):
            if not pd.isnull(df_temp.iloc[i]):
                words_roles = df_temp.iloc[i].split(':')[:2]
                if len(words_roles) > 1:
                    emojis.append(":" + words_roles[1] + ":")
                    message_tosend += words_roles[0] + \
                                      ":" + words_roles[1] + ":" + "\n"
                else:
                    message_tosend += df_temp.iloc[i] + "\n"
        message = None
        for message_id in messages_to_monitor:
            # logger.info(message_id)
            message = await welcome_channel.fetch_message(message_id)
            # logger.info(message.content)
            if message.content[:85] in message_tosend:
                break
        if message_tosend == message.content:
            # if the message content is the same as teh new content, we can just ignore it
            break

        await message.edit(content=message_tosend)
        for emoji_str in emojis:
            # We need to make sure if emoji in list if not we can add it.
            emoji_symbol = emoji_data.loc[emoji_data['Shortcode']
                                          == emoji_str, 'Symbol'].values[0]
            if emoji_symbol:
                await message.add_reaction(emoji_symbol)

            role = emoji_data.loc[emoji_data['Shortcode']
                                  == emoji_str, 'Role'].values[0]
            if role:
                await createRole(ctx, role, messages=False)
    await ctx.send("Messages have been edited")


@bot.event
async def on_raw_reaction_add(payload):
    our_guild = bot.get_guild(payload.guild_id)
    message_id = payload.message_id
    if message_id in messages_to_monitor:
        logger.info("We just reacted to the message we want")
        logger.info(payload.emoji)
        member = discord.utils.get(
            our_guild.members, id=payload.user_id)
        emoji_data = pd.read_excel("..\Emoji Data.xlsx")
        if payload.emoji.name not in emoji_data['Symbol'].unique():
            logger.info(f"{payload.emoji.name} is not in our list")
            return
        role_name = emoji_data.loc[emoji_data['Symbol']
                                   == payload.emoji.name, 'Role'].values[0]
        role_to_add = discord.utils.get(our_guild.roles, name=role_name)
        if member and role_to_add:
            await member.add_roles(role_to_add)


@bot.event
async def on_raw_reaction_remove(payload):
    our_guild = bot.get_guild(payload.guild_id)
    message_id = payload.message_id
    if message_id in messages_to_monitor:
        logger.info("We just removed a message we want")
        logger.info(payload.emoji)
        member = discord.utils.get(
            our_guild.members, id=payload.user_id)
        emoji_data = pd.read_excel("..\Emoji Data.xlsx")
        if payload.emoji.name not in emoji_data['Symbol'].unique():
            logger.info(f"{payload.emoji.name} is not in our list")
            return
        role_name = emoji_data.loc[emoji_data['Symbol']
                                   == payload.emoji.name, 'Role'].values[0]
        role_to_remove = discord.utils.get(our_guild.roles, name=role_name)
        if member and role_to_remove:
            await member.remove_roles(role_to_remove)
        logger.info(payload.emoji)


@bot.command(name='create_role', description="creates a role '!create_role role_name1 role_name2'",
             brief='creates a role through command')
async def createRole(ctx, *args, messages=True):
    our_guild = ctx.guild
    if (not await checkRole(ctx, messages)):
        return
    if len(args) > 0:
        for arg in args:
            arg = arg.strip()
            if discord.utils.get(our_guild.roles, name=arg) == None:
                await our_guild.create_role(name=arg)
                if messages:
                    await ctx.send(f"Created role {arg}")
            else:
                if messages:
                    await ctx.send(f"The role {arg} is already implemented")


async def checkRole(ctx, messages=True):
    # Might check for a bunch of roles to see if they work
    # Admin
    roles = ["SIGGRAPH_Chair", "Admin"]
    our_guild = ctx.guild
    roles_needed = []
    for role in roles:
        roles_needed.append(discord.utils.get(our_guild.roles, name=role))
    member_in_question = discord.utils.get(
        our_guild.members, name=ctx.message.author.name)
    # If there is role in the array that fits. we can use the command
    if (set(roles_needed) & set(member_in_question.roles)):
        if messages:
            await ctx.send(f"You do have the permissions to use this command")
        return True
    else:
        if messages:
            await ctx.send(f"You can not use this command")
        return False


# This is to do a sanity check on the emoji


@bot.command(name='test_emoji_data', hidden=True)
async def emojiData(ctx):
    our_guild = ctx.guild
    emoji_data = pd.read_excel("..\Emoji Data.xlsx")
    for index, row in emoji_data.iterrows():
        if (":" in row['Symbol']):
            # emoji = bot.get_emoji(row["Discord_ID"])
            # message = await ctx.send(row['Shortcode'])
            # await message.add_reaction("<"+row['Shortcode']+row["Discord_ID"]+">")
            pass
        else:
            message = await ctx.send(row['Symbol'])
            await message.add_reaction(row['Symbol'])
    # emoji_data.to_excel("..\Emoji Data.xlsx", index=False)


# Commands don't work when this is set
# @bot.event
# async def on_message(message):
#     logger.info(f"Message from {message.author}: {message.content}")

bot.run(TOKEN)
