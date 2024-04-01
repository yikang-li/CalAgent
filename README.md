## Preparation 
1. Install required libraries
```
pip3 install -r requirement.txt
```
2. Setup your own configuration in `config.ini` based on `config_example.ini`
```bash
cp config_example.ini config.ini
```
3. Run the code on your server


## Run
默认通过环境变量来配置config.ini文件路径， 默认采用./config.ini
```
export PA_CONFIG_PATH=./config_server.ini
```
Run the bot in the background
```bash
touch run.log
nohup python3 app.py > run.log 2>&1 & tail -f run.log         
```
If you want to kill the program, use `ps -ef | grep app.py | grep -v grep` find the PID and `kill PID` to kill it.