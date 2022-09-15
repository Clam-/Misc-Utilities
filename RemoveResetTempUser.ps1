
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

# Example usage:
#Remove-LocalUserCompletely -Name 'myuser'
Write-Host "Cleaning user..."
Remove-LocalUserCompletely -Name 'BAHN'
Write-Host "Remaking user..."
New-LocalUser -Name "BAHN" -Description "Description of this account." -NoPassword
Write-Host "Done. Device is ready for new user. You can close this window now (it will automatically close in 30 seconds)"
Start-Sleep -Seconds 30
