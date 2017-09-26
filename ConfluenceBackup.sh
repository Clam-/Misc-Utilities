#!/bin/bash
USERNAME=$USERNAME
PASSWORD=$PASSWORD
INSTANCE=$INSTANCE
#example.atlassian.net
MAILTO=$MAILTO
#error@location.com
MAILFROM=$MAILFROM
#device@location.com

# Subject, body
sendMail() {
	php -r "mail('$MAILTO', '$1', '$2', 'From: $MAILFROM');";
}

NOWFILE=`date +%Y%m%d-%H%M%S.zip`




RESP=$(curl -s -o /dev/null -w "%{http_code}" -u $USERNAME:$PASSWORD -X POST -H "Content-Type: application/json" https://$INSTANCE/wiki/rest/obm/1.0/runbackup -d '{"cbAttachments":"true" }')

if [ "$RESP" != "200" ]
then
	sendMail "Confluence Backup Error" "Error at runbackup"
	exit 1
fi
PERCENT="0"
COUNTER=0
while [ $COUNTER -lt 40]; do
	PERCENT=$(curl -s -u $USERNAME:$PASSWORD -X GET -H "Content-Type: application/json" https://$INSTANCE/wiki/rest/obm/1.0/getprogress.json | jq .alternativePercentage)
	if [ $PERCENT = "100%" ] then
		break
	fi
	sleep 50
done
if [ $PERCENT != "100%" ] then
	sendMail "Confluence Backup Error" "Error at getprogress: $PERCENT"
	exit 1
fi

FNAME=$(curl -s -u $USERNAME:$PASSWORD -X GET -H "Content-Type: application/json" https://$INSTANCE/wiki/rest/obm/1.0/getprogress.json | jq .fileName)

if [[ $FNAME == temp/filestore* ]] then
	curl -L -f -o $NOWFILE -u $USERNAME:$PASSWORD "https://$INSTANCE/wiki/download/$FNAME" || { sendMail "Confluence Backup Error" "Error downloading $FNAME" ; exit 1; }
	#temp/filestore/3e7fe66d-867a-46e0-a252-940f03966e73
else
	sendMail "Confluence Backup Error" "Error at fileName"
	exit 1
fi
# upload to dropbox
./dropbox_uploader.sh -q upload $NOWFILE $NOWFILE || { sendMail "Confluence Backup Error" "Error at upload $NOWFILE"; exit 1; }
rm $NOWFILE
sendMail "Confluence Backup Success" "Backup of $NOWFILE complete."

