Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase

$logPath = Join-Path $env:APPDATA 'KeyboardCompanion\battery_log.csv'

[xml]$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        WindowStyle="None" AllowsTransparency="True" Background="Transparent"
        Width="250" Height="126" Topmost="True" ShowInTaskbar="True"
        ResizeMode="NoResize" Title="K10 HE Battery">
  <Border CornerRadius="18" Background="#F20D1017" BorderBrush="#798491" BorderThickness="1" Padding="16">
    <Grid>
      <Grid.RowDefinitions>
        <RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/>
      </Grid.RowDefinitions>
      <Grid Grid.Row="0">
        <TextBlock Text="KEYCHRON K10 HE" Foreground="#27C8EE" FontSize="11" FontWeight="SemiBold"/>
        <Button Name="CloseButton" Content="×" HorizontalAlignment="Right" Width="22" Height="22"
                Foreground="#BFC9DA" Background="Transparent" BorderThickness="0" FontSize="16" Padding="0"/>
      </Grid>
      <Grid Grid.Row="1" Margin="0,6,0,3">
        <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
        <TextBlock Name="PercentText" Text="--%" Foreground="#F4F7FF" FontSize="34" FontWeight="Bold" VerticalAlignment="Center"/>
        <Border Grid.Column="1" Name="BatteryBorder" Width="70" Height="29" CornerRadius="6" BorderBrush="#BFC9DA" BorderThickness="2" VerticalAlignment="Center">
          <Grid Margin="3">
            <Border Name="BatteryFill" HorizontalAlignment="Left" Width="0" CornerRadius="3" Background="#27C8EE"/>
          </Grid>
        </Border>
      </Grid>
      <TextBlock Grid.Row="2" Name="StatusText" Text="Waiting for Keyboard Companion…" Foreground="#BFC9DA" FontSize="12"/>
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
$closeButton.Add_Click({ $window.Close() })

function Update-Widget {
    if (-not (Test-Path -LiteralPath $logPath)) {
        $statusText.Text = 'Waiting for Keyboard Companion…'
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
        $batteryFill.Width = [Math]::Max(1, 62 * $pctValue / 100)
        if ($pctValue -le 15) { $batteryFill.Background = '#FF5B65' }
        elseif ($pctValue -le 35) { $batteryFill.Background = '#F5B84B' }
        else { $batteryFill.Background = '#27C8EE' }
        $state = switch ([int]$last.charging) { 1 {'Charging'} 2 {'Fully charged'} default {'On battery'} }
        $link = switch ($last.transport) { 'usb' {'USB'} 'dongle' {'2.4 GHz'} 'bluetooth' {'Bluetooth'} default {$last.transport} }
        $statusText.Text = "$state  •  $link  •  $($last.voltage_mv) mV"
    } catch {
        $statusText.Text = 'Waiting for the next battery reading…'
    }
}

$timer = New-Object Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromSeconds(2)
$timer.Add_Tick({ Update-Widget })
$timer.Start()
Update-Widget
$window.ShowDialog() | Out-Null
