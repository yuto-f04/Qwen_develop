param(
    [Parameter(Mandatory=$true)]
    [string]$Url
)

$ffmpegPath = "C:\Users\yutof\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"

yt-dlp -x --audio-format wav --download-sections "*0-10" --ffmpeg-location $ffmpegPath $Url
