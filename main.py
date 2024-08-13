import traceback
import discord
#import json
import requests
import pymongo
from pymongo import MongoClient
from discord.ext import commands, tasks
from discord import app_commands, User
from motor.motor_asyncio import AsyncIOMotorClient
#import os
#import regex
import datetime

intents = discord.Intents.default()
intents.message_content = True
#client = discord.Client(intents=intents)
bot = commands.AutoShardedBot(intents=intents, command_prefix="!")

commandsync = False



@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    # with open('messageid.json', '', encoding='utf-8') as meslistjson:
    #     bot.messagelist = json.load(meslistjson)
    #logChannel = client.get_channel(1176213194239389797)
    #await logChannel.send("The Watcher is online.")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Custom Games"))
    global commandsync
    mongo = MongoClient("MONGODB_URL_HERE") # you need a mongodb database for the bot to store game data. example layout: mongodb+srv://username:password@cluster1.0.mongodb.net/
    bot.db = mongo.auedb
    await bot.wait_until_ready()
    #bot.tree.clear_commands(guild=None)
    #await bot.tree.sync()
    #bot.tree.add_command(add_embed)
    #bot.tree.add_command(add_playerdata)
    #bot.tree.add_command(remove_embed)
    if not commandsync:
        bot.tree.add_command(add_embed)
        bot.tree.add_command(add_playerdata)
        bot.tree.add_command(remove_embed)
        await bot.tree.sync()
        update_gamedb.start(bot)
        update_playerdb.start(bot)
        update_leaderboard.start(bot)
        commandsync = True
        print("sync!")
    commandlist = await bot.tree.fetch_commands()
    print("command list: ", commandlist)
    #print("bot running!")
    #mongo = MongoClient("")
    #bot.db = mongo.auedb
    #currdir = os.listdir()
    #print("aoedb!!!: ", bot.db)
    print("bot running!")
       
# exampledatamessage = {
#     "channelid": 1207738613274779720,
#     "messageid": 0,
#     "type": "", #leaderboard or tournaments
# }

#def checkcustomgame(ctx):
def alloweduse(ctx):
    allowedlist = [183940132129210369, 610854994576670728] #allow you to use the commands
    print('author check', ctx.user.id in allowedlist)
    return ctx.user.id in allowedlist
    


@app_commands.command(name="add_playerdata", description="add player info to the leaderboard")
@app_commands.describe(
    playerid="player id of aoe4world"
)
@app_commands.check(alloweduse)
async def add_playerdata(interaction, playerid: int, discord: User = None):
    try:
        checkifplayerexist = requests.get(url=f"https://aoe4world.com/api/v0/players/{playerid}" , params={
        })
        #print('player exist!!', checkifplayerexist)
        if checkifplayerexist.status_code != 200:
            await interaction.response.send_message("Error: that playerid was not found", ephemeral=True)
        else:
            try:
                playerdata = checkifplayerexist.json()
                gamewin = []
                gameloss = []
                win2v2v2v2 = []
                winffa = []
                getgamelist = bot.db.customgamedata.find({"$or": [{"win": str(playerid)}, {"loss": str(playerid)}]})
                for game in getgamelist:
                    if game['team2v2v2v2'] == True or game['ffagame'] == True:
                        
                        #print('gamelist', game["_id"])
                        if str(playerid) in game['loss']:
                            gameloss.append(str(game["_id"]))
                            #print("gameloss!!")
                        elif str(playerid) in game['win']:
                            gamewin.append(str(game["_id"]))
                            #print("gamewin!!")
                        #print('gamelist', gamewin)
                        if game['team2v2v2v2'] == True and str(playerid) in game['win']:
                            #print("yes a win2v2v2v2!")
                            win2v2v2v2.append(str(game["_id"]))
                        if game['ffagame'] == True and str(playerid) in game['win']:
                            #print("yes a ffagame!")
                            winffa.append(str(game["_id"]))
                bot.db.playerdata.update_one( {'_id': str(playerid)},
                        {'$set': {'discordid': str(discord.id), 'steamid': playerdata['steam_id'], 'win': gamewin, 'loss': gameloss, 'name': playerdata["name"], 'win2v2v2v2': win2v2v2v2, 'winffa': winffa}},
                        upsert=True
                        )
                await interaction.response.send_message(f"the player [{playerdata['name']}]({playerdata['site_url']}) <@{discord.id}> has been added to database", suppress_embeds=True, ephemeral=True)
                #print('player exist!!', checkifplayerexist.status_code)
            except:
                await interaction.response.send_message("Error: failed to update database", ephemeral=True)
    except:
        await interaction.response.send_message("Unknown Error!!", ephemeral=True)
        print('unknown error!')
    #print("add_playerdata ran!!", playerid, discord)
    
       
@app_commands.command(name="add_embed", description="add leaderboard embed")
@app_commands.check(alloweduse)
@app_commands.choices(
    type=[discord.app_commands.Choice(name="leaderboard", value=1), discord.app_commands.Choice(name="tournaments", value=2)],
)
async def add_embed(interaction, type: discord.app_commands.Choice[int]):
    print("add_leaderboard ran!! ")
    channelid = interaction.channel
    if type.name == "leaderboard":
        embed = gen_embed(interaction)
        sendmess = await channelid.send(embed=embed)
        sendmess
        #print("add messag!e", await sendmess.fetch())
        try:
            bot.db.messagedata.update_one( {'_id': str(sendmess.id)},
                {'$set': {'channelid': str(channelid.id), 'type': "leaderboard"}},
                upsert=True
                )
            await interaction.response.send_message("embed leaderboard was made!")
        except:
            await interaction.response.send_message("Error!: failed to add leaderboard to database so it will not update!")
        print("yes leaderboard")
    elif type.name == "tournaments":
        print("yes tournaments")

    print("add_leaderboard end")
    
@app_commands.command(name="remove_embed", description="remove leaderboard embed")
@app_commands.check(alloweduse)
async def remove_embed(interaction, message_id: str):
    print('remove_embed ran!')
    leaderdata = bot.db.messagedata.find_one({'_id': message_id})
    #channel = bot.get_channel(int(leaderdata['channelid']))
    if leaderdata is None:
        await interaction.response.send_message("Error!: could not find message!")
    elif leaderdata:
        channel = bot.get_channel(int(leaderdata['channelid']))
        message = await channel.fetch_message(int(leaderdata['_id']))
        await message.delete()
        bot.db.messagedata.delete_one({'_id': message_id})
        await interaction.response.send_message("deleted message successfully!")
    else:
        await interaction.response.send_message("Error!: unknown")
       
@tasks.loop(minutes=15)
async def update_leaderboard(self):
    print("update_leaderboard ran!")
    leaderdata = bot.db.messagedata.find()
    #embed = gen_embed(self)
    for board in leaderdata:
        embed = gen_embed(self)
        channel = bot.get_channel(int(board['channelid']))
        message = await channel.fetch_message(int(board['_id']))
        await message.edit(embed=embed)
    #testgetmessage = channel.fetch_message(1217640482998587422)
    #await message.edit(embed=embed)
   # print('get message', message)
    


        
@tasks.loop(minutes=30)
async def update_gamedb(ctx):
    print('update game db!')
    grabgamedata = requests.get(url="https://aoe4world.com/api/v0/players/2078108/games" , params={
        "api_key":"APIKEY", #your API key you get from aoe4world.com
        "kind": "custom"
    })
    #"profile_ids": 2078108,
    #print("grab url!!", grabgamedata.url)
    grabgamedata = grabgamedata.json().get('games')
    #print('grab game data!!', len(grabgamedata))
    playercount = 0
    today = datetime.datetime.today()
    week_ago = today - datetime.timedelta(days=14) #change how long the bot will keep your custom game data
    #print("today", today, "and week", week_ago)
    for game in grabgamedata:
       # print("get game datev2", game['updated_at'])
        changetime = datetime.datetime.strptime(game['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        #print("get game date!!!!!!", game['updated_at'], "and", changetime)
        if changetime >= week_ago:
            playercount = 0
            winlist = []
            losslist = []
            playerperteam = []
            totalplayercount = 0
            if game['kind'] == "custom":
                #print('test teams', len(game['teams']), game['game_id'], game)
                for team in game['teams']:
                    #print('team for loop!!', playercount, len(team))
                    playerperteam.append(len(team))
                    totalplayercount += len(team)
                    for player in team:
                        #print("player")
                        #print('test player', len(team), player['player']["profile_id"], player['player']["name"], player['player']["result"], player['player'])
                        if player['player']["result"] == "win":
                            winlist.append(str(player['player']["profile_id"]))
                        elif player['player']["result"] == "loss":
                            losslist.append(str(player['player']["profile_id"]))
               
                if len(game['teams']) == 4:
                    if playerperteam.count(2) == 4:
                        team2v2v2v2 = True
                    else:
                        team2v2v2v2 = False
                else:
                    team2v2v2v2 = False
                    
                if len(game['teams']) == 8:
                    if playerperteam.count(1) == 8:
                        FFAgame = True
                    else:
                        FFAgame = False
                else:
                    FFAgame = False
                    
                # if len(game['teams']) == 8:
                #     if playerperteam.count(1) == 2:
                #         FFAgame = True
                #     else:
                #         FFAgame = False
                # else:
                #     FFAgame = False
                    #print("team 8 yes?", playerperteam.count(1))
                bot.db.customgamedata.update_one(
                        {'_id': str(game['game_id'])},
                        {'$set': {'started_at': game['started_at'], 'updated_at': (game['updated_at']), 'kind': game['kind'], 'map': game['map'], 'leaderboard': game['leaderboard'], 'ongoing': game['ongoing'], 'win': winlist, 'loss': losslist, 'team_count': len(game['teams']), 'player_team': playerperteam, 'team2v2v2v2': team2v2v2v2, 'ffagame': FFAgame, 'totalplayers': totalplayercount}},
                        upsert=True
                    )
        if game:
            allwinlist = []
            alllosslist = []
            allplayerperteam = []
            alltotalplayercount = 0
            if game['kind'] == "custom":
                #print('test teams', len(game['teams']), game['game_id'], game)
                for team in game['teams']:
                    #print('team for loop!!', playercount, len(team))
                    allplayerperteam.append(len(team))
                    alltotalplayercount += len(team)
                    for player in team:
                        #print("player")
                        #print('test player', len(team), player['player']["profile_id"], player['player']["name"], player['player']["result"], player['player'])
                        if player['player']["result"] == "win":
                            allwinlist.append(str(player['player']["profile_id"]))
                        elif player['player']["result"] == "loss":
                            alllosslist.append(str(player['player']["profile_id"]))
               
                if len(game['teams']) == 4:
                    if allplayerperteam.count(2) == 4:
                        allteam2v2v2v2 = True
                    else:
                        allteam2v2v2v2 = False
                else:
                    allteam2v2v2v2 = False
                    
                if len(game['teams']) == 8:
                    if allplayerperteam.count(1) == 8:
                        allFFAgame = True
                    else:
                        allFFAgame = False
                else:
                    allFFAgame = False

                bot.db.allcustomgamedata.update_one(
                        {'_id': str(game['game_id'])},
                        {'$set': {'started_at': game['started_at'], 'updated_at': (game['updated_at']), 'kind': game['kind'], 'map': game['map'], 'leaderboard': game['leaderboard'], 'ongoing': game['ongoing'], 'win': allwinlist, 'loss': alllosslist, 'team_count': len(game['teams']), 'player_team': allplayerperteam, 'team2v2v2v2': allteam2v2v2v2, 'ffagame': allFFAgame, 'totalplayers': alltotalplayercount}},
                        upsert=True
                    )
            else:
                print('game not custom!!')
        else:
            bot.db.customgamedata.delete_one({'_id': str(game['game_id'])})
    #print('total player countv2', playercount)
    #checkplayercount = For p in 
    
@tasks.loop(minutes=15)
async def update_playerdb(ctx):
    playerdata = bot.db.playerdata.find()
    print("update player data", playerdata)
    for p in playerdata:
        playerid = p['_id']
        #print("update playerid", playerid)
        #try:
        checkifplayerexist = requests.get(url=f"https://aoe4world.com/api/v0/players/{playerid}" , params={
        })
        #print('player exist!!', checkifplayerexist)
        if checkifplayerexist.status_code != 200:
            #await interaction.response.send_message("Error: that playerid was not found")
            print("Error: that playerid was not found", p)
        else:
            #try:
                playerdata = checkifplayerexist.json()
                gamewin = []
                gameloss = []
                win2v2v2v2 = []
                loss2v2v2v2 = []
                winffa = []
                lossffa = []
                getgamelist = bot.db.customgamedata.find({"$or": [{"win": str(playerid)}, {"loss": str(playerid)}]})
                for game in getgamelist:
                    if game['team2v2v2v2'] == True or game['ffagame'] == True:
                        #print('gamelist', game["_id"])
                        if str(playerid) in game['loss']:
                            gameloss.append(str(game["_id"]))
                            #print("gameloss!!")
                        elif str(playerid) in game['win']:
                            gamewin.append(str(game["_id"]))
                            #print("gamewin!!", )
                        if game['team2v2v2v2'] == True and str(playerid) in game['win']:
                            #print("yes a win2v2v2v2!")
                            win2v2v2v2.append(str(game["_id"]))
                        if game['team2v2v2v2'] == True and str(playerid) in game['loss']:
                            #print("yes a win2v2v2v2!")
                            loss2v2v2v2.append(str(game["_id"]))
                        if game['ffagame'] == True and str(playerid) in game['win']:
                            #print("yes a ffagame!")
                            winffa.append(str(game["_id"]))
                        if game['ffagame'] == True and str(playerid) in game['loss']:
                            #print("yes a ffagame!")
                            lossffa.append(str(game["_id"]))
                        #print('gamelist', gamewin)
                bot.db.playerdata.update_one( {'_id': str(playerid)},
                        {'$set': {'steamid': playerdata['steam_id'], 'win': gamewin, 'loss': gameloss, 'name': playerdata["name"], 'win2v2v2v2': win2v2v2v2, 'winffa': winffa, 'loss2v2v2v2': loss2v2v2v2, 'lossffa': lossffa}},
                        upsert=True
                        )
                #await interaction.response.send_message(f"the player [{playerdata['name']}]({playerdata['site_url']}) <@{discord.id}> has been added to database", suppress_embeds=True, ephemeral=True)
                #print('player exist!!', checkifplayerexist.status_code)
                print(f"the player {playerdata['name']} data was updated")
                # except:
                #     #await interaction.response.send_message("Error: failed to update database")
                #     print("Error: failed to update database", playerid)
        # except:
        #     #await interaction.response.send_message("Unknown Error!!")
        #     print('unknown error!')
        #print("update_playerdata ran!!", playerid, discord)
    
    #print('update player data end')
        


def gen_embed(interaction):
    embed = discord.Embed(title="Leaderboard - Custom Games")
    embed.set_footer(text="this message update every 30 min...")
    playerDBdata = bot.db.playerdata.find().sort('win', -1)
    #playerDBsort = bot.db.playerdata.sort()
    #print("gen embed DB", playerDBdata)
    #Rank | Player Name | Games Played Total | Games Won Total | FFA wins | 2v2v2v2 wins | W/L
    ranknumber = 0
    playerlist1 = ""
    playerlist2 = ""
    playerlist3 = ""
    for p in playerDBdata:
        #ranknumber = 0
        ranknumber += 1
        totalgame = len(p['win']) + len(p['loss'])
        total2v2v2v2 = len(p['win2v2v2v2']) + len(p['loss2v2v2v2'])
        totalffa = len(p['winffa']) + len(p['lossffa'])
        #print("gen embed DB", p['name'], "total",totalgame, "winloss", winlossratio, ranknumber)
        if len(p['win']) == 0 and len(p['loss']) == 0:
            #print("yes both == 0")
            winlossratio = 0.0
        else:
            winlossratio = (len(p['win']) / totalgame)*100
        #print("gen embed DB", p['name'], "total",totalgame, "winloss", winlossratio, ranknumber)
        
        textforlist1 = f"{ranknumber} | {p['name']} | {round(winlossratio, 2)}%"
        #print("get length test", len(textforlist1))
        #if textforlist1 is 
        playerlist1 += textforlist1 + "\n"
        playerlist2 += f"{ranknumber} | {totalgame} | {len(p['win'])}\n"
        playerlist3 += f"{ranknumber} | {totalffa} | {len(p['winffa'])} | {total2v2v2v2} | {len(p['win2v2v2v2'])}\n"
    
    
    embed.add_field(name="Rank | Player Name | W/L", value=playerlist1, inline=False)
    embed.add_field(name="Rank | TOTAL GAMES | TOTAL WINS", value=playerlist2, inline=False)
    embed.add_field(name="Rank | FFA GAMES | WINS | 2v2v2v2 GAMES | WINS", value=playerlist3, inline=False)
    
    return embed







bot.run('BOTTOKEN') #your bot token