# gmail_unsubscribe
This tool enables you to easily unsubscribe from email lists. The script works by accessing your email account and identifying emails that contain links or headers for unsubscribing. It then groups these emails by sender and generates a convenient HTML page that allows you to quickly unsubscribe using those links. With this tool, you can easily declutter your inbox and take control of your email subscriptions.

Script

![An example of how to execute the main script](https://github.com/luarmr/gmail_unsubscribe/blob/main/assets/command_line.png?raw=true)


Output

![example of the output that you can expect from the main script](https://github.com/luarmr/gmail_unsubscribe/blob/main/assets/output.png?raw=true)

## Prerequisites

### STEP 1

To download your credentials, please follow these steps:

https://developers.google.com/gmail/api/quickstart/python#set_up_your_environment

### STEP 2
To install the necessary requirements, you can either use the `requirement.txt` file or execute the following command:




```
⚡ pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib beautifulsoup4 jinja2 tqdm retrying
```

## Execution

```
⚡ ./main.py -h
usage: main.py [-h] [--before BEFORE] --after AFTER --credentials CREDENTIALS --output OUTPUT [--extra-search-param EXTRA_SEARCH_PARAM]

options:
  -h, --help            show this help message and exit
  --before BEFORE       before this time the emails wont be contemplated. MM/DD/YY
  --after AFTER         after this time the emails wont be contemplated. MM/DD/YY
  --credentials CREDENTIALS
                        path to the credentials.json check "https://developers.google.com/gmail/api/quickstart/python"
  --output OUTPUT       where the html file should be generated
  --extra-search-param EXTRA_SEARCH_PARAM
                        add extra string to narrow down the search: example "NOT label:inbox"
```

recommend using a one-month window for the "after" parameter. This will enable you to capture the relevant data within a reasonable timeframe without extending the execution of the script too much.

```
⚡ ./main.py --after 11/11/2022 --credentials credentials.json --output=output_2.html
```



