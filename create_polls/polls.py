from flask import Flask, request, jsonify
import json

def create_polls(question, prompts): #parameters (question will be str , prompts will be a  list)
    poll_structure = []

    polls_name_lst = polls_name(prompts)

    blocks = {"type": "header","text": {"type": "plain_text", "text": f"Question: {question}", "emoji": True}}
    poll_structure.append(blocks)
    poll_structure.append({"type": "divider"})

    for num_poll in polls_name_lst:
        poll_structure.append(num_poll)
    poll_structure.append({"type": "divider"})

    return poll_structure

    
def polls_name(prompt_name): #parameter will be a list and return a list 
	lst = []
	for i in range(len(prompt_name)):
		context = {"type": "context", "elements": [{"type": "mrkdwn", "text": "0 voted."}]}
		poller = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{prompt_name[i]}*"
            }
        }
		lst.append(poller)
		lst.append(context)
	return lst

def poll_button(prompts):
	lst = []
	for txt in prompts:
		poller = {
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"*{txt}*"
			},
			"accessory": {
				"type": "button",
				"text": {
					"type": "plain_text",
					"text": "Vote",
					"emoji": True
				},
				"style": "primary",
				"value": f"{txt}",
				"action_id": "action_poll"
			}
		}
		lst.append(poller)
	return lst
		
def get_index_by_value(payload, value):
	for index, item in enumerate(payload):
		if item.get('type') == "section":
				txt = item['text']['text'].replace('*', '')
				if txt == value:
					return index
	return -1

def update_poll_vote(payload, username, image_url, value):
	index = get_index_by_value(payload, value)
	try:
		tally = {"type": "image",
			"image_url": f"{image_url}",
			"alt_text": f"{username}"
			}
		for section in payload:
			if section.get('type') == "section":
				txt = section['text']['text'].replace('*', '')
				if txt == value:
					payload_info = payload[index+1]['elements']
					
					num = int(payload_info[0]['text'].split()[0])+1
	
					payload_info[0]['text'] = f"{num} voted"
					if len(payload_info) <= 9:
						payload_info.append(tally)
		return payload
	except Exception as e:
		print(f'something wrongs in update_poll_payload {e}')





def update_poll_modal(payload):
	num_prompts = len(payload['blocks']) - 1
	dispatch_action = {
			"dispatch_action": True,
			"type": "input",
			"element": {
				"type": "plain_text_input",
				"action_id": "plain_text_input-action"
			},
			"label": {
				"type": "plain_text",
				"text": "Enter your poll",
				"emoji": True
			}
		}
	payload['blocks'].insert(-1, dispatch_action)

	return payload
	
# this remove the keys from your payload ex bot_id, team_id
def remove_bad_keys(payload, bad_keys):
	return {key: value for key, value in payload.items() if key not in bad_keys}
	

def checks_user_vote_kitchen(value, user_id):
	try:
		# Load the existing JSON data from the file
		with open('jsonfile/kitchen/kitchen_storage.json', 'r') as file:
			json_data = json.load(file)
	except (FileNotFoundError, json.JSONDecodeError):
		json_data = {}
	if user_id not in json_data:
		json_data[user_id] = {[value]}
		return True
	elif user_id in json_data:
		if value not in json_data[user_id]:
			json_data[user_id].append(value)
			return True
		else:
			return False

def store_poll_payload(ts: str, payload: list):
	try:
		# Load the existing JSON data from the file
		with open('jsonfile/poll/storepoll.json', 'r') as file:
				json_data = json.load(file)
	except (FileNotFoundError, json.JSONDecodeError):
		json_data = {}

	try:
		if ts not in json_data:
			json_data.update({ts: payload})
		else:
			json_data[ts]["blocks"] = payload
		with open('jsonfile/poll/storepoll.json', 'w') as file:
			json.dump(json_data, file, indent=4)
	except Exception as e:
		print(f'something wrongs in store_poll_payload {e}')


def check_vote(message_ts: str, user_id: str):
	try:
		# Load the existing JSON data from the file
		with open('jsonfile/poll/list_voted.json', 'r') as file:
				lst_voted = json.load(file)
	except (FileNotFoundError, json.JSONDecodeError):
		lst_voted = {}
	try:
		if message_ts not in lst_voted:
			lst_voted.update({message_ts : [user_id]})

			with open('jsonfile/poll/list_voted.json', 'w') as filer:
				json.dump(lst_voted, filer, indent=4)

			return True
		else:

			if user_id in lst_voted[message_ts]:
				return False

			else:
				lst_voted.update({message_ts : [user_id]})

				with open('jsonfile/poll/list_voted.json', 'w') as filer:
					json.dump(lst_voted, filer, indent=4)
					
				return True
		
	except Exception as e:
		print(f'something wrongs in check_vote {e}')






	



	
	
	
        

	
	

