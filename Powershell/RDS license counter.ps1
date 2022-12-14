$sum = 0
For ($i = 0 ; $i -le 10 ; $i++) {
if ($a = $null)
{
break
} else
{
[int32]$a = ((get-WmiObject Win32_TSLicenseKeyPack | Where-Object KeyPackType -like '2' | select-object 'AvailableLicenses').AvailableLicenses)[$i]
$sum = $sum + $a
}
}
Write-Host $sum