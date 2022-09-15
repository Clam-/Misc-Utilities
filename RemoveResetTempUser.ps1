
#function from https://superuser.com/a/1570605
function Remove-LocalUserCompletely {

    Param(
        [Parameter(ValueFromPipelineByPropertyName)]
        $Name
    )

    process {
        $user = Get-LocalUser -Name $Name -ErrorAction Stop

        # Remove the user from the account database
        Remove-LocalUser -SID $user.SID

        # Remove the profile of the user (both, profile directory and profile in the registry)
        Get-CimInstance -Class Win32_UserProfile | ? SID -eq $user.SID | Remove-CimInstance
    }
}
function LogOffUser {
    Param(
        [Parameter(ValueFromPipelineByPropertyName)]
        $Name
    )

    process {
        #https://stackoverflow.com/a/49042770
        $sessions = (((quser) -replace '^>', '') -replace '\s{2,}', ',' | ConvertFrom-Csv) | Where-Object {$_.USERNAME -eq 'banh user'}
        foreach ($session in $sessions)
        {
          logoff $session.SESSIONNAME
        }
    }
}

# Example usage:
#Remove-LocalUserCompletely -Name 'myuser'
# log off user
LogOffUser

Write-Host "Cleaning user..."
Remove-LocalUserCompletely -Name 'Banh User'
Write-Host "Remaking user..."
New-LocalUser -Name "Banh User" -Description "Description of this account." -NoPassword | Set-LocalUser -PasswordNeverExpires $true
Add-LocalGroupMember -Member 'Banh User' -Group Users
Write-Host "Done. Device is ready for new user. You can close this window now (it will automatically close in 30 seconds)"
Start-Sleep -Seconds 30