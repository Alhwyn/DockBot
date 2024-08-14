import os
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from dotenv import find_dotenv, load_dotenv
import create_polls.polls
import json
import gemini


load_dotenv(find_dotenv())

# when deploying to production remove the  except in the setup_routes() functions

class DockBot:
    def __init__(self, slack_bot_token, slack_signing_secret, slack_bot_user_id):
        #variables
        self.slack_bot_token = slack_bot_token
        self.slack_signing_secret = slack_signing_secret
        self.slack_bot_user_id = slack_bot_user_id

        self.flask_app = Flask(__name__)
        self.client = WebClient(token=self.slack_bot_token)

        self.app = App(token=self.slack_bot_token, 
                       signing_secret=self.slack_signing_secret)
        self.handler = SlackRequestHandler(self.app)

        self.setup_routes()
        self.setup_events_and_commands()

        # Custom variables
    
        self.channel_id = None
        
        #custom modules
        self.createpoll = create_polls.polls
        self.gemini = gemini

        #MASTER KEY
        self.MasterPass = 'DockDock'
        
    def setup_routes(self):
        @self.flask_app.route("/slack/events", methods=["POST"])
        def slack_events():
            return self.handler.handle(request)

    def setup_events_and_commands(self):

# -------------------------------App Mention--------------------------------------------------------------

        @self.app.event("app_mention")
        def handle_mentions(body, say, message, logger, client):
            text = body['event']['text']
            user = body['event']['user']
            ts = body['event']['ts']
            channel_id = body['event']['channel']
            try:

                mention = f"<@{self.slack_bot_user_id}>"
                text = text.replace(mention, "").strip()

                initial_mes = say(text="thinking...", thread_ts=ts)

                gemini_reply = self.gemini.gemini_ai(text, user)
 
                client.chat_update(text=f"<@{user}> {gemini_reply}", 
                                   channel=channel_id, 
                                   ts=initial_mes['ts'])
   
                # stores the converstion history k is how much converstion man it store
                self.gemini.StoresMemory(user_id=user, inputter=text, output=gemini_reply, k=2)

            except Exception as e:
                logger.error(f"Error handling app mentioning \n {e}")

        @self.app.event("message")
        def handle_message_events(body, logger):
            logger.info(body)

        # This is a test Command text
        @self.app.command("/command")                           
        def help_command(ack, say, command, logger):
            ack()

            with open('jsonfile/command.json') as file:
                    json_data = json.load(file)
                    say(text=json_data)

# -------------------------------Pricing Command--------------------------------------------------------------
        # Activate the Price Command
        @self.app.command("/pricing")
        def pricing_command(ack, say, body,  command, logger, client):
            ack()
            trigger_id = body['trigger_id']
            try:
                # Open the json file 
                with open('jsonfile/pricing.json') as file:
                    
                    # Display the json file into a modal
                    json_data = json.load(file)
                    client.views_open(trigger_id=trigger_id, 
                                      view=json_data)

            except Exception as e:
                logger.error(f"Error Handling in command pricing {e}")

        # Listener Function if the user press Okay
        @self.app.view("pricing_view_id")
        def handle_pricing_submission(ack, body, logger):
            ack()
            
            try:
                print('pricing modals works')
            except Exception as e:
                logger.error(f"Error Handling handle_pricing_submission {e}")

# -------------------------------Poll Command--------------------------------------------------------------
        
        # Activates the Poll command
        @self.app.command("/create-poll")
        def create_poll(ack, say, command, client, body,  logger):
            ack()
            try:
                self.channel_id = body['channel_id']
                # Loads the modal
                trigger_id = body['trigger_id']
                with open('jsonfile/poll_modal.json') as file:
                    json_data = json.load(file)
                    client.views_open(trigger_id=trigger_id, 
                                      view=json_data)
   
            except Exception as e:
                logger.error(f"Error Handling the Event {e}")

        # Listener Function when user add a section for thier poll 
        @self.app.action("poll_button_clicked")
        def poll_modal_clicked(ack, body, client, logger):
            ack()
            try:
                # Removes the Keys that makes the modal not readable for the views_update()
                bad_keys = ["previous_view_id",  
                            "root_view_id", 
                            "app_id", 
                            "external_id", 
                            "app_installed_team_id", 
                            "bot_id", "team_id", "id",
                            "private_metadata", 
                            "state", "hash"
                            ]

                user_payload = body['view']
                view_id = body['view']['id']

                # Readable Payload for views_update()
                clean_payload = self.createpoll.remove_bad_keys(user_payload, bad_keys)

                # Updates the modal
                poll = self.createpoll.update_poll_modal(clean_payload)
                
                # Update the Modal by adding the section
                client.views_update(view_id=view_id, 
                                    view=poll)

            except Exception as e:
                logger.error(f"Error handling poll_button_clicked \n{e}")

        # Extract the Data from the modal when the user press "Submit"
        @self.app.view("view_id")
        def view_submission(ack, body, logger, say, client):
            ack()
            try:
                poll_values = body["view"]["state"]["values"]
                user_id = body['user']['id']
                username = body['user']['username']
                

                # This take the Values from the user input of the poll
                extracted_poll_values = [num['plain_text_input-action']['value'] for num in poll_values.values()]

                response = self.client.conversations_members(channel=self.channel_id)
                user_ids = response['members']

                # Extract the Question in str and the polls into a list
                poll_question, *poll_poll = extracted_poll_values
                
                # Creates the Poll message
                comm = self.createpoll.create_polls(poll_question, poll_poll) 

                # Create the Button for interaction of the Poll
                buttons = self.createpoll.poll_button(poll_poll)
                # Outputs the Message in the Slack channel 2 messages
                messagepayload = say(text='post_message_payload', 
                                     channel=self.channel_id, 
                                     blocks=comm
                                    )

                button_payload = say(text='post_button_payload', 
                                     channel=self.channel_id, 
                                     blocks=buttons
                                    )

                self.createpoll.store_poll_payload(ts=button_payload['ts'], 
                                                   payload=messagepayload['message'])


            except Exception as e:
                logger.error(f'Error handling view_id \n{e}')



        # Listener Function for when the user Interact with the voting button
        @self.app.action('action_poll')
        def handle_poll_action(ack, body, say, client, logger):
            ack()
            try:
                username = body['user']['username'] 
                message_ts_butt = body['message']['ts'] 
                #message_ts = self.payload_poll.get(message_ts_butt)['ts']
                channel_id = body['channel']['id'] 
                user_id = body['user']['id'] 
                image_url = self.client.users_profile_get(user=user_id)['profile']['image_24']  
                user_value = body['actions'][0]['value'] 
                with open('jsonfile/poll/storepoll.json', 'r') as file:
                    json_data = json.load(file)
          
                user_payload = json_data[message_ts_butt]['blocks']
                message_ts = json_data[message_ts_butt]['ts']
            
                 # If the User hasnt Voted this will tally thier vote and add their image
                poll_bool = self.createpoll.check_vote(message_ts=message_ts, 
                                                       user_id=user_id)

                if poll_bool:
                    poll = self.createpoll.update_poll_vote(user_payload, user_id, image_url, user_value)
                
                    client.chat_update(text='',
                                        channel=body["channel"]["id"],
                                        ts=message_ts,
                                        blocks=poll
                                    )

         
                    self.createpoll.store_poll_payload(ts=message_ts_butt, payload=poll)
                else:
                    client.chat_postEphemeral(channel=channel_id, 
                                              user=user_id, 
                                              text='It seems like you already voted 🤖'
                                             )

            except Exception as e:
                logger.error(f"Error Handling the action {e}")

# -------------------------------doggo Command--------------------------------------------------------------
        @self.app.command('/doggo')
        def doggo_command(ack, say, body,  command, logger, client):
            ack()
            trigger_id = body["trigger_id"]
            try:
                with open("jsonfile/doggo.json") as f:
                    json_data = json.load(f)
                client.views_open(trigger_id=trigger_id, 
                                  view=json_data
                                 )

            except Exception as e:
                logger.error(f"Error handling the doggo command {e}")

        @self.app.view('doggo_view_id')
        def doggo_view_handler(ack, say, body, logger, client):
            ack()
            try:
                print('doggo modals works')
            except Exception as e:
                logger.error(f"Error Handling handle_pricing_submission {e}")
# -------------------------------Info Command--------------------------------------------------------------
        @self.app.command("/info")
        def info_command(ack, say, body, command, logger, client):
            ack()
            trigger_id = body['trigger_id']
            try:
                with open("jsonfile/info_modal.json") as f:
                    json_data = json.load(f)
                client.views_open(trigger_id=trigger_id, 
                                  view=json_data
                                 )
            except Exception as e:
                logger.error(f"Error Handling /info command {e}")

        @self.app.view("info_id")
        def info_handler(ack, body, logger):
            ack()
            try:
                print('info modals works')
            except Exception as e:
                logger.error(f"Error Handling /info modal\n {e}")

# -------------------------------Rental price Command--------------------------------------------------------------
        @self.app.command("/space-rental")
        def info_command(ack, say, body, command, logger, client):
            ack()
            trigger_id = body['trigger_id']
            try:
                with open("jsonfile/rental_price.json") as f:
                    json_data = json.load(f)
                client.views_open(trigger_id=trigger_id, 
                                  view=json_data
                                 )
            except Exception as e:
                logger.error(f"Error Handling /space-rental command {e}")

        @self.app.view("info_id")
        def info_handler(ack, body, logger):
            ack()
            try:
                print('info modals works')
            except Exception as e:
                logger.error(f"Error Handling /space-rental modal\n {e}")
# -------------------------------test Command--------------------------------------------------------------
        @self.app.command("/test")
        def test_command(ack, say, command, logger, client):
            ack()
            try:
                result = client.conversations_history(channel='C0782V89Q6T')
                conversations_history = result['messages']
                for message in conversations_history:
                    var = message['ts']
                    print(var)
            except Exception as e:
                logger.error(f"Error Handling /test\n {e}")
#
# -------------------------------Introduction Command--------------------------------------------------------------
        @self.app.command("/introduction")
        def introduction_command(ack, say, command, logger, client, body):
            ack()
            trigger_id = body['trigger_id']
            channel_id = body['channel_id']
            user_id = body['user_id']

            mystery_word = body['text']
            if mystery_word == self.MasterPass:
                try:
                    with open('jsonfile/introduction.json') as f:
                        json_data = json.load(f)

                    client.chat_postMessage(channel=channel_id, 
                                            blocks=json_data['blocks'],
                                            text='b'
                                        )

                except Exception as e:
                    logger.error(f"Error Handling /introduction command \n {e}")
            else:
                client.chat_postEphemeral(channel=channel_id, 
                                              user=user_id, 
                                              text='Commands Requires a master Key!!🔐'
                                             )


        @self.app.action("introduction-action")
        def test_command(ack, say, logger, client, body):
            ack()
            trigger_id = body['trigger_id']
            try:
                with open('jsonfile/info_modal.json') as f:
                    json_data = json.load(f)
                client.views_open(trigger_id=trigger_id, 
                                  view=json_data,
                                  text='hi'
                                 )
            except Exception as e:
                logger.error(f"Error Handling intrduction message modal\n {e}")


# ------------------------------- FeedBackCommand --------------------------------------------------------------
        @self.app.command("/suggestion")
        def test_command(ack, say, command, logger, client, body):
            ack()
            trigger_id = body['trigger_id']
            try:
                with open("jsonfile/suggestion.json") as f:
                    json_data = json.load(f)
                client.views_open(trigger_id=trigger_id, 
                                  view=json_data,
                                  text='hi'
                                 )
            except Exception as e:
                logger.error(f"Error Handling /suggestion command \n {e}")

        @self.app.view("suggestion_id")
        def info_handler(ack, logger, body, client):
            ack()
            try:
                poll_values = body["view"]["state"]["values"]
                message_value = [inner['value'] for outer in poll_values.values() for inner in outer.values()]

                #this will be sent to me aka Alhwyn
                with open("jsonfile/suggestion_message.json") as file:
                    json_file = json.load(file)
                    json_file['attachments'][0]['blocks'][2]['text']['text'] = message_value[0]

                client.chat_postMessage(channel='U06LB3164UU', 
                                        attachments=json_file["attachments"], 
                                        text='ALERT: '
                                       )
            except Exception as e:
                logger.error(f"Error Handling suggestion view\n {e}")


# ------------------------------- Kitchen Wishes --------------------------------------------------------------

        @self.app.command('/kitchen-wishes')
        def kitchen_command(ack, say, command, logger, client, body):
            ack()
            channel_id = body['channel_id'] 
            try:
                # ima add the passcode later
                with open("jsonfile/kitchen/kitchen_message.json") as file:
                    json_file = json.load(file)

                with open("jsonfile/kitchen/kitchen_button.json") as file1:
                        button_file = json.load(file1)
   
                bob = say(text=json_file, channel=channel_id)
                say(text=button_file, channel=channel_id)
                with open('jsonfile/kitchen/kitchen_paylaod.json', 'w') as file2:
                    print(bob)
                    json.dump(bob.data, file2, indent=4)       

            except Exception as e:
                logger.error(f"Error Handling /kitchen-wishes command \n {e}")

        @self.app.action('kitchen_id')
        def handle_poll_action(ack, body, say, client, logger):
            ack()
            trigger_id = body['trigger_id']
            try:
                with open('jsonfile/kitchen/kitchen_modal.json') as file:
                    json_file = json.load(file)
                client.views_open(trigger_id=trigger_id, 
                                  view=json_file,
                                  text='kit'
                                 )
            except Exception as e:
                logger.error(f"Error handling Kitchen Wishes button\n {e}")

        
        @self.app.view("kitchen_view")
        def info_handler(ack, body, logger):
            ack()
            try:
                data = body["view"]["state"]
                value = [v['plain_text_input-action']['value'] for k, v in data['values'].items() if 'plain_text_input-action' in v and 'value' in v['plain_text_input-action']][0]
                print(value)
                with open("jsonfile/kitchen/kitchen_storage.json") as file:
                    json_file = json.load(file)

            except Exception as e:
                logger.error(f"Error Handling /kitchen-wishes modal modal\n {e}")

    def run(self):
        self.flask_app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    signing_secret = os.getenv("SlACK_SIGNING_SECRET")
    user_id = os.getenv("SLACK_BOT_USER_ID")
    bot = DockBot(slack_token, signing_secret, user_id)
    bot.run()

