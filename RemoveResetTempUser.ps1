#TODO:
#       Task Schedule this. Not sure about this. Could cause problems if device loaned over longer period...

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

#disable welcome screen thing
#[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System]
#"EnableFirstLogonAnimation"=dword:00000000
#[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon]
#"EnableFirstLogonAnimation"=dword:00000000
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name EnableFirstLogonAnimation -Value 0
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" -Name EnableFirstLogonAnimation -Value 0
# disable privacy prompt
#[HKEY_CURRENT_USER\Software\Policies\Microsoft\Windows\OOBE]
#"DisablePrivacyExperience"=dword:00000001
#[HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\OOBE]
#"DisablePrivacyExperience"=dword:00000001
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\OOBE" -Name DisablePrivacyExperience -Value 1
#Disable Edge first login prompt
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Edge" -Name DisablePrivacyExperience -Value 1

Write-Host "Cleaning user..."
Remove-LocalUserCompletely -Name 'BANH User'
Write-Host "Remaking user..."
New-LocalUser -Name "BANH User" -FullName "BANH User" -Description "Description of this account." -NoPassword | Set-LocalUser -PasswordNeverExpires $true
Add-LocalGroupMember -Member 'BANH User' -Group Users
Write-Host "Done. Device is ready for new user. You can close this window now (it will automatically close in 30 seconds)"
Start-Sleep -Seconds 30
