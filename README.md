# Installation Instructions

To get started, you'll need to install the required libraries. Run the following command:

```
pip install requests
```
and
```
pip install telebot
```
you may need to
```
pip install dotenv
```
Now you need to obtain your API key and secret key. To do this, please register on the following site and create a new key pair in the API section on the left:

***[API Keys](https://fusionbrain.ai/)***

After that, create a Telegram bot. You can do this by searching for ***@BotFather*** in Telegram and following the instructions to obtain your bot management token.

### ***Important:*** 
*In the new version of the project, you will need to create 3 accounts and obtain a key pair from each of them. This will allow the bot to use 3 keys simultaneously, bypassing restrictions. Please do not use your personal accounts for this purpose. In case of a ban on the site, you will be solely responsible for it.*

Finally, enter the necessary data for the code to function properly in the ***Config.py*** file by replacing the lines ```(os.getenv('api_key'))``` with your keys, or create a .env file where all personal data will be stored.

## You can also read the official documentation for the API.
***[Fusion Brain Documentation](https://fusionbrain.ai/docs/ru/doc/api-dokumentaciya/)***
