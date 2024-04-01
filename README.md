# CalAgent (Calendar Agent)
An agent to manage your calendar based on the Wechat (maybe more in the future).

## Preparation 
Follow these steps to set up your environment for running the application.

### 1. Install required libraries
```
pip3 install -r requirement.txt
```
### 2. Configure Your Settings
Setup your own configuration in `config.ini` based on `config_example.ini`
```bash
cp config_example.ini config.ini
```
### 3. Run the code on your server

The application uses `config.ini` for its default configuration. You can alter the configuration by specifying a different file through an environment variable:
```
export PA_CONFIG_PATH=./config_server.ini
```

To run the bot in the background and log its output:
```bash
touch run.log
nohup python3 app.py > run.log 2>&1 & tail -f run.log         
```

If you need to stop the application, use `ps -ef | grep app.py | grep -v grep` find the PID and `kill PID` to kill it.
