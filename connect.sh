#! /bin/sh
#Last update 20230908
#Develpoer: Andre Cheung, @jiansuo
#LookOut Connect Bash shell script move PTZ camera, get images and send to LookOut

#function to move camera to preset, get image and post to LookOut
#first parameter is preset and second parameter is LookOut camera endpoint
move_get_post ()  {
	curl -s http://camera.host.name/axis-cgi/com/ptz.cgi?gotoserverpresetname=$1 --anyauth --user username:Password
	sleep 9
	curl -s --output temp.jpg http://camera.host.name/axis-cgi/jpg/image.cgi?resolution=1920X1080 --anyauth --user username:Password
	curl $2 -H "content-type: image/jpeg" --data-binary @temp.jpg -s --output result.txt &
}

#LookOut camera endpoints
LookOut1="https:/...."
LookOut2="https:/...."
LookOut3="https:/...."
LookOut4="https:/...."
LookOut5="https:/...."
LookOut6="https:/...."

#x is the variable of guard tour cycle
x=0
#cycle is the input of number guard tour. Default is 5.
cycle=${1:-5}

#image is the variable of the number of images send to LookOut
image=0
start=`date -Iseconds`
startsecond=$(date +%s)


while [ $x -lt $cycle ]
do

move_get_post preset1 LookOut1
move_get_post preset2 LookOut2
move_get_post preset3 LookOut3
move_get_post preset4 LookOut4
move_get_post preset5 LookOut5
move_get_post preset6 LookOut6

image=$(($image+6))
x=$(($x+1))
echo "`date -Iseconds`: $x out of $cycle cycles are run." > cycle.log

done


end=`date -Iseconds`
endsecond=$(date +%s)

echo -e "LookOut AI detection result:\nIn the last $(($endsecond-$startsecond)) seconds between $start and $end.\n$x out of $cycle cycles are run. $image images are send to LookOut camera $lookoutCamName.\n" | tee summary.txt
