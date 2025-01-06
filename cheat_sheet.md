
## Initialize Dev env on MacOS

### Go to the correct source dir

    cd /Users/jsdorais/Documents/LEDDisplay/PixelPulseNeo

### Activate Python Virtual Env

    source venv/bin/activate

### Start VS Code from the right environment

    code .

## Starting a commnd

    python -m Matrix.driver.executor -c tides -d 200

## Send back changes to GitHub

### Check what are local changes

    git status

### Add files to commit

    git add <filename>

### Commit files

    git commit

### Send changes

    git push

## Get channges on the Pie

### ssh to the pie

    ssh jsdorais@ledjeanse.local

### go to the right directory

    cd ~/dev/PixelPulseNeo

### pull changes

    git pull

### restart the service

    sudo systemctl restart pixel-pulse-neo
