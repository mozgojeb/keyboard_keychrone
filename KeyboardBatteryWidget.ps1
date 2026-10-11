Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase

$logPath = Join-Path $env:APPDATA 'KeyboardCompanion\battery_log.csv'
$configPath = Join-Path $env:APPDATA 'KeyboardCompanion\config.json'
$createdNew = $false
$widgetMutex = [System.Threading.Mutex]::new($true, 'Local\KeyboardCompanion.BatteryWidget', [ref]$createdNew)
if (-not $createdNew) {
    $widgetMutex.Dispose()
    return
}

[xml]$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        WindowStyle="None" AllowsTransparency="True" Background="Transparent"
        Width="390" Height="190" Topmost="True" ShowInTaskbar="True"
        ResizeMode="NoResize" Title="K10 HE Battery">
  <Border CornerRadius="19" Background="#F20D1017" BorderBrush="#798491" BorderThickness="1" Padding="24">
    <Grid>
      <Grid.RowDefinitions>
        <RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/>
      </Grid.RowDefinitions>
      <Grid Grid.Row="0">
        <TextBlock Text="KEYCHRON K10 HE" Foreground="#27C8EE" FontFamily="Segoe UI" FontSize="14" FontWeight="SemiBold" VerticalAlignment="Center"/>
        <Button Name="CloseButton" Content="&#215;" HorizontalAlignment="Right" Width="28" Height="28"
                Foreground="#BFC9DA" Background="Transparent" BorderThickness="0" FontFamily="Segoe UI" FontSize="21" Padding="0"/>
      </Grid>
      <Grid Grid.Row="1" Margin="0,12,0,8">
        <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
        <TextBlock Name="PercentText" Text="--%" Foreground="#F4F7FF" FontFamily="Segoe UI" FontSize="48" FontWeight="Bold" VerticalAlignment="Center"/>
        <Border Grid.Column="1" Name="BatteryBorder" Width="86" Height="40" CornerRadius="6" BorderBrush="#BFC9DA" BorderThickness="2" VerticalAlignment="Center" Margin="0,0,7,0">
          <Grid Margin="4">
            <Border Name="BatteryFill" HorizontalAlignment="Left" Width="0" CornerRadius="3" Background="#27C8EE"/>
          </Grid>
        </Border>
      </Grid>
      <TextBlock Grid.Row="2" Name="StatusText" Text="Waiting for Keyboard Companion&#8230;" Foreground="#BFC9DA" FontFamily="Segoe UI" FontSize="14" TextTrimming="CharacterEllipsis"/>
    </Grid>
  </Border>
</Window>
'@

$reader = New-Object System.Xml.XmlNodeReader $xaml
$window = [Windows.Markup.XamlReader]::Load($reader)
$percentText = $window.FindName('PercentText')
$statusText = $window.FindName('StatusText')
$batteryFill = $window.FindName('BatteryFill')
$closeButton = $window.FindName('CloseButton')

$window.Add_MouseLeftButtonDown({ $window.DragMove() })
$closeButton.Add_Click({
    try {
        $settings = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        $settings.widget_enabled = $false
        $json = $settings | ConvertTo-Json -Depth 30
        [System.IO.File]::WriteAllText($configPath, $json, [System.Text.UTF8Encoding]::new($false))
    } catch { }
    $window.Close()
})

function Update-Widget {
    try {
        $settings = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        if (-not $settings.widget_enabled) {
            $window.Close()
            return
        }
    } catch { }
    if (-not (Test-Path -LiteralPath $logPath)) {
        $statusText.Text = 'Waiting for Keyboard Companion...'
        return
    }
    try {
        $last = Import-Csv -LiteralPath $logPath | Select-Object -Last 1
        if (-not $last) { return }
        $age = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [long][double]$last.epoch
        if ($age -gt 30) {
            $statusText.Text = 'Keyboard sleeping or disconnected'
            return
        }
        $pctValue = if ($last.displayed_pct) { [int][double]$last.displayed_pct } else { [int][double]$last.raw_pct }
        $pctValue = [Math]::Max(0, [Math]::Min(100, $pctValue))
        $percentText.Text = "$pctValue%"
        $batteryFill.Width = [Math]::Max(1, 72 * $pctValue / 100)
        if ($pctValue -le 15) { $batteryFill.Background = '#FF5B65' }
        elseif ($pctValue -le 35) { $batteryFill.Background = '#F5B84B' }
        else { $batteryFill.Background = '#27C8EE' }
        $state = switch ([int]$last.charging) { 1 {'Charging'} 2 {'Fully charged'} default {'On battery'} }
        $link = switch ($last.transport) { 'usb' {'USB'} 'dongle' {'2.4 GHz'} 'bluetooth' {'Bluetooth'} default {$last.transport} }
        $bullet = [char]0x2022
        $statusText.Text = "$state  $bullet  $link  $bullet  $($last.voltage_mv) mV"
    } catch {
        $statusText.Text = 'Waiting for the next battery reading...'
    }
}

$timer = New-Object Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromSeconds(2)
$timer.Add_Tick({ Update-Widget })
$timer.Start()
Update-Widget
try {
    $window.ShowDialog() | Out-Null
} finally {
    $widgetMutex.ReleaseMutex()
    $widgetMutex.Dispose()
}
