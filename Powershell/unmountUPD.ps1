#Отмонтирует принудительно UPD пользователя на srv-rds-host. Использовать при отсутствии сессии пользователя, но залипшем UPD.
#Переменной UPDSharePath указано место хранения UPD коллекции.

$username = Read-Host 'User logon name'

$UPDSharePath="\\srv-vmstorage\UserDisks\RDS_Main"
 
#Get's User SID
$strSID = (New-Object System.Security.Principal.NTAccount($username)).Translate([System.Security.Principal.SecurityIdentifier]).value
 
#Creates UPD path String
$diskname=$UPDSharePath+"\UVHD-"+$strsid+".vhdx"
 
#Finds the disk and dismounts it
Get-DiskImage $diskname | Dismount-DiskImage