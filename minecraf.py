"""
FoxxySocksBot - A telegram bot made for the FurRIT Gaming chat
Author: Ryan Marlin (Maru)
Purpose: Keep track of information relevant to the members
Future: Keep adding features, deal with possible sql injection issues
"""

import logging
from mcstatus import MinecraftServer
import mysql.connector as mariadb
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackContext
from telegram import Update
import config


botUpdate = Updater(token=config.token, use_context=True)

dispatcher = botUpdate.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

server = MinecraftServer.lookup(config.mchost)

"""
Method: Welcome
Purpose: Triggered by handler upon new user entering. Give user the rules, restrict their access and give them a simple
test against bots. 
Future: Pretty simple, changes needed are miniumal
"""
def welcome(update: Update, context: CallbackContext):
    message = ", welcome gamer"
    new = update.message.new_chat_members

    for member in new:
        name = str(member.first_name)
        newMessage = name.strip() + message
        context.bot.send_message(chat_id=update.message.chat_id, text=newMessage)

"""
Method: Help
Purpose: Post help for commands
Future: Update with new features
"""
def help(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.message.chat_id, text=config.help)


"""
Method: isAdmin
Purpose: Simple check to see if the user who sent a message is an admin or creator of the chat in question
Future: I am sure there is a better way to do it. But this will work
"""
def isAdmin(context, message):
    return context.bot.get_chat_member(message.chat_id, message.from_user.id).status in [
        'administrator', 'creator']


"""
Method: Delete Message
Purpose: Helper function to delete a message from the chat
Future: None
"""
def deleteMessage(message, context):
    context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)


"""
Method: Database Query
Purpose: Run queries and return results
Future: A bit rushed together, could use some cleaning up
"""
def dbQuery(query, ret):
    dbConnect = mariadb.connect(user=config.dbuser, password=config.dbpass, database=config.db, host=config.dbhost)
    cursor = dbConnect.cursor()
    cursor.execute("USE Furrit")

    cursor.execute(query)
    value = None
    try:
        value = cursor.fetchall()
    except Exception as e:
        pass
    dbConnect.commit()
    dbConnect.close()
    if ret:
        return value


"""
Method: Add User
Purpose: Use a message to get the name and uid to make a new user in the database
Future: This is probably bad security, I don't care right now
"""
def addUser(message):
    name = message.from_user.first_name
    uid = message.from_user.id
    auquery = "insert into gamer (name, uid) values (\"%s\", \"%s\")" % (name, uid)

    dbQuery(auquery, False)



"""
Method: Print Codes
Purpose: Get codes for a user and print them all nice
Future: Works well, not really expandable
"""
def printCodes(uid, bot, message):
    pcquery = "Select * from gamer where uid = %s" % (uid)
    values = dbQuery(pcquery, True)
    values = values[0]
    types = ["Switch", "Steam", "Origin", "Xbox", "Epic", "GoG", "PSN", "Uplay", "3ds", "Minecraft"]
    string = "Name: " + values[0] + "\n"
    i = 0

    for value in values[2:]:
        if value:
            string += types[i] + ": " + str(value) + "\n"
        i += 1

    bot.send_message(chat_id=message.chat_id, text=string)


"""
Method: Get Codes
Purpose: Get UID for Print Codes either from message or DB
Future: Not sure
"""
def getCodes(update: Update, context: CallbackContext):
    uid = update.message.from_user.id
    message = update.message.text.split(" ")

    if len(message) == 1:
        printCodes(uid, context.bot, update.message)
    elif len(message) == 2:

        gcquery = "Select * from gamer where name like \"%" + message[1] + "%\""
        userValues = dbQuery(gcquery, True)[0]
        if userValues:
            printCodes(userValues[1], context.bot, update.message)
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text=message[1] + " not found")
    else:
        context.bot.send_message(update.message.chat_id, text="Please specify only one user")


"""
Method: Split
Purpose: Splits an array into several length 2 arrays
Future: I think this is fine
"""
def split(arr, size):
    arrs = []
    while len(arr) > size:
        piece = arr[:size]
        arrs.append(piece)
        arr = arr[size:]
    arrs.append(arr)
    return arrs


"""
Method: Add Code
Purpose: Run the add command, create user in DB if one does not exist, add services if given
Future: Bit of a mess, could probably be broken out into multiple functions. Method for specifying the col name is
probably an avenue for sqlinjection. Shouldn't be due to the possible fields check
"""
def addCode(update: Update, context: CallbackContext):
    message = update.message
    user = message.from_user.id
    acquery = "select * from gamer where uid = %s" % user
    records = dbQuery(acquery, True)
    if not records:
        addUser(message)
    fields = message.text.split(" ")[1:]
    FIELD_ENUM = ["Switch", "Minecraft", "Steam", "Origin", "Xbox", "PSN", "Epic", "GoG", "Uplay", "3DS"]
    if len(fields) == 0:
        context.bot.send_message(chat_id=message.chat_id, text="Added")
        return
    elif len(fields) % 2 != 0:
        context.bot.send_message(chat_id=message.chat_id, text="Invalid add command, please ask an admin")
        return
    codes = split(fields, 2)
    for code in codes:
        if code[0] not in FIELD_ENUM:
            context.bot.send_message(chat_id=message.chat_id, text=str(code[0]) + " is not a valid service")
            return
        upQuery = "UPDATE gamer SET %s = \"%s\" WHERE uid = \"%s\"" % (str(code[0].lower()), str(code[1]), str(user))

        try:
            dbQuery(upQuery, False)

        except Exception as e:
            print("Error: User " + user + e)
            context.bot.send_message(chat_id=message.chat_id, text="Something went wrong")
    printCodes(user, context.bot, update.message)


"""
Method: Names
Purpose: Get the names of registered users for easy use of /codes
Future: Should keep working fine
"""
def names(update: Update, context: CallbackContext):
    query = "SELECT name FROM gamer"
    name_list = dbQuery(query, True)
    string = "Users: "
    for part in name_list:
        string += part[0] + ", "

    context.bot.send_message(chat_id=update.message.chat_id, text=string[:-2])


"""
Method: Get Service Codes
Purpose: Lets a user list all the users who use a service and what their codes are
Future: I still feel weird about using the enum to col names thing, but it works and I think it's safe for now
"""
def getServiceCodes(update: Update, context: CallbackContext):
    FIELD_ENUM = ["Switch", "Minecraft", "Steam", "Origin", "Xbox", "PSN", "Epic", "GoG", "Uplay", "3DS"]
    message = update.message
    serviceMessage = message.text.split(" ")
    if len(serviceMessage) == 2:
        service = serviceMessage[1]
    else:
        context.bot.send_message(chat_id=message.chat_id, text="One service at a time please")
        return
    if service in FIELD_ENUM:
        gscquery = "Select name, " + service + " from gamer where " + service + " is not null;"
        values = dbQuery(gscquery, True)
        string = "Entries for " + service + ":\n"
        for value in values:
            string += value[0] + ": " + value[1] + '\n'
        context.bot.send_message(chat_id=message.chat_id, text=string)

    else:
        context.bot.send_message(chat_id=message.chat_id, text=service + " is not a valid service (check capitalization)")


"""
Method: Minecraft Server Status
Purpose: Check the status of the various minecraft servers we run
Future: Track more servers as they exist
"""
def MCServerStatus(update: Update, context: CallbackContext):
    status = server.status()
    players = "Players online:\n"
    onlinePlayers = status.players.sample

    if onlinePlayers:
        for player in status.players.sample:
            players += player.name + ", "
        players = players[:-2]

    message = config.mcname + ":\nThe server replied with a ping of " + str(status.latency) + " ms and there are " + str(status.players.online) + " people on.\n"
    message = message + players

    context.bot.send_message(chat_id=update.message.chat_id, text=message)


# Handler for welcome message and user checks
welcomeHandle = MessageHandler(Filters.status_update.new_chat_members, welcome, pass_chat_data=True)
dispatcher.add_handler(welcomeHandle)

# Handler for help command
ruleHandle = CommandHandler('help', help, pass_chat_data=True)
dispatcher.add_handler(ruleHandle)

# Handler for the add command
addHandle = CommandHandler('add', addCode, pass_chat_data=True)
dispatcher.add_handler(addHandle)

# Handler for the codes command
getHandle = CommandHandler('codes', getCodes, pass_chat_data=True)
dispatcher.add_handler(getHandle)

# Handler for the names command
nameHandle = CommandHandler('names', names, pass_chat_data=True)
dispatcher.add_handler(nameHandle)

# Handler for Minecraft server stuff
mcHandle = CommandHandler('mc', MCServerStatus, pass_chat_data=True)
dispatcher.add_handler(mcHandle)

# Handler for Service command
GSCHandle = CommandHandler('service', getServiceCodes, pass_chat_data=True)
dispatcher.add_handler(GSCHandle)

botUpdate.start_polling(clean=True)
