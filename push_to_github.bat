@echo off
echo ====================================================
echo Pushing Vulture Bot to GitHub
echo Repo: https://github.com/therasajs14-max/vulture-bot.git
echo ====================================================
git push -u origin main
if %ERRORLEVEL% EQU 0 (
    echo ====================================================
    echo SUCCESS: Project pushed to GitHub successfully!
    echo ====================================================
) else (
    echo ====================================================
    echo PUSH FAILED. If authentication is needed, enter your GitHub Personal Access Token.
    echo ====================================================
)
pause
