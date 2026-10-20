@echo off
rem Upload the Windows build to Steam (SteamPipe). Run "npm run dist" in the desktop folder first.
rem 1) Set STEAMCMD to steamcmd.exe in the Steamworks SDK (tools\ContentBuilder\builder\steamcmd.exe)
rem 2) Replace the AppID and the depot ID in app_build.vdf with yours
rem 3) Run this file and sign in with your Steamworks account (Steam Guard code on the first run)
set STEAMCMD=C:\steamworks_sdk\tools\ContentBuilder\builder\steamcmd.exe
set /p STEAMUSER=Steamworks user name: 
"%STEAMCMD%" +login %STEAMUSER% +run_app_build "%~dp0app_build.vdf" +quit
pause
