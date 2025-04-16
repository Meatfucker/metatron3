# metatron3

The third iteration of my machine learning discord bot that uses the avernus API server 
which can be obtained here: https://github.com/Meatfucker/avernus

It has a variety of slash commands and an llm powered chatbot. See below for detailed descriptions of functionality.

# Install:

 - Create a python venv or conda environment
 - Enter the environment.
 - Install the requirements file via pip.
 - Edit the example configs in configs and rename them to not have the example extension.
 - Run metatron.py

configs/avernus.json:

| Key           | Value      | Description                                                                     |
|---------------|------------|---------------------------------------------------------------------------------|
| ip            |"127.0.0.1 | The ip address or hostname of the avernus API server                            |
| port          |6969       | The port of the avernus API server                                              |
| llm_model     |"Goekdeniz-Guelmez/Josiefied-Qwen2.5-7B-Instruct-abliterated-v2"| The Huggingface model repo to the model to use for the chat LLM                 |
| sdxl_model    |"misri/zavychromaxl_v100"     | The Huggingface model repo for the SDXL model to use                            |
| mtg_llm_model |"cognitivecomputations/Llama-3-8B-Instruct-abliterated-v2"| This is the Huggingface repo for the LLM to use for card titles and flavor text |

configs/discord.json

| Key                          | Value           | Description                                                                                                                                                                              |
|------------------------------|-----------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| token                        | "yourtokenhere" | This is your discord bot token generated using the discord dev portal.                                                                                                                   |
| max_user_queue               | 3               | The maximum amount of items any particular user can have queued.                                                                                                                         |
| max_user_history_message     | 20              | This is the maximum amount of history to store per user.                                                                                                                                 |
| mtg_gen_three_pack_send_link | false           | Whether to send a hardcoded link with the three pack. You probably want this off and I plan on making it configurable in the future. Currently used for integration into my own website. |

configs/twitch.json

| Key                 | Value                | Description                                                                                                                                      |
|---------------------|----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| twitch_enabled      | false                | Whether to start the twitch client for twitch integration                                                                                        |
| token               | "yourtwitchtokenhere | bot user twitch token                                                                                                                            |
| client_id           | "yourclientid        | bot user client id                                                                                                                               |
| client_secret       | "yourclientsecret    | bot user client secret                                                                                                                           |
| channel_name        | "channelname"        | The name of the twitch channel                                                                                                                   |
| channel_id          | "channelid"          | The twitch channel id of the channel                                                                                                             |
| channel_token       | "channeltoken"       | The channel token that was created by the channel owner                                                                                          |
| refresh_token       | "refreshtoken"       | The channel refresh token that was created along the other channel token                                                                         |
| reward_name         | "Your Reward Name"   | The name of the channel point redemption reward to watch for                                                                                     |
| token_expires_at    | 1                    | This is the unix timestamp the current token expires at. You generally do not need to set this as itll be managed by the twitch client if enabled |
| card_reward_channel | 435234532452345      | The discord channel id of the channel to post the twitch redeemed cards in                                                                       |

configs/channels/somediscordchannelid.json

| Key         | Value                  | Description                                                                                                       |
|-------------|------------------------|-------------------------------------------------------------------------------------------------------------------|
| lora_name   | "somelora.safetensors" | This is the name of the lora located on the avernus API server to use in this channel when generating magic cards |
| lora_prompt | "some prompt to add"    | This prompt gets added to the mtg card gens that use the lora.                                                    |


# Features:

![](/assets/readme/slash_commands.png)

## Chatbot:

Simply tag the bot with its name to interact with it. It keeps a per user history 
of the users conversation with it but cannot otherwise see chat.

The LLM model which is used can be configured in configs/avernus.json. It takes
huggingface repo names. Note that the first time a model is used (such as the first run)
there will be a large delay while the avernus server downloads the model.

There is also a /clear_chat_history command to empty your users chat history

![](/assets/readme/llm_chat.png)

## /sdxl_gen:

This generates an image with the sdxl model specified in configs/avernus.json

- prompt: Is your prompt
- negative_prompt: The generated image will move away from this. Useful to avoid unwanted things in gens.
- width: The width in pixels of the image to generate. Defaults to 1024 Be careful of setting this too high as itll require more video memory and over a certain point cause deformed generations.
- height: Same as above but tall style
- batch_size: The number of images to generate at once. Combined with image resolution this can have a direct and large effect on video memory usage. If you are having lots of avernus Out Of Memory issues, try decreasing batch size and/or resolution
- lora_name: this is the filename(including safetensors extesion) of a lora located in appropriate avernus server lora directory.
- enhance_promt: This will send the user prompt to the default chat llm to be "improved"

![](/assets/readme/sdxl_gen.png)

## /flux_gen

This generates an image using the flux.dev model, which is higher quality than sdxl but slower and takes more memory while running.

- prompt: Is your prompt
- width: The width in pixels of the image to generate. Defaults to 1024 Be careful of setting this too high as itll require more video memory and over a certain point cause deformed generations.
- height: Same as above but tall style
- batch_size: The number of images to generate at once. Combined with image resolution this can have a direct and large effect on video memory usage. If you are having lots of avernus Out Of Memory issues, try decreasing batch size and/or resolution
- - enhance_promt: This will send the user prompt to the default chat llm to be "improved"

![](/assets/readme/flux_gen.png)

## /mtg_gen

This generates a satire magic card based on the users prompt using a combination of the chosen sdxl model, as well as the llm specified at "mtg_llm_model" in configs/avernus.json. 

It will include the discord server icon as a set icon, a random artist for the artist name, and the user name and server name for the copyright. 

THESE ARE SATIRE CARDS AND NOT MEANT TO BE USED COMMERCIALLY.

![](/assets/readme/mtg_gen.png)

## /mtg_gen_three_pack

Same as above but generates three at a time, which is also what is triggered if twitch integration is enabled and the appropriate channel reward triggered.

![](/assets/readme/mtg_gen_three_pack.png)

# TODO

- Let a user know if a gen fails for any reason
- add modals for slash commands




