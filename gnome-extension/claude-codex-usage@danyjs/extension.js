import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import GLib from 'gi://GLib';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const REFRESH_SECONDS = 60;
const WIDGET_COMMAND = 'claude-usage';
const WIDGET_PID_PATH = GLib.build_filenamev([
    GLib.get_user_cache_dir(), 'claude-usage', 'widget.pid',
]);

function percent(value) {
    return Math.round(Math.max(0, Math.min(1, Number(value) || 0)) * 100);
}

function widgetCommand() {
    return GLib.find_program_in_path(WIDGET_COMMAND) ?? GLib.build_filenamev([
        GLib.get_home_dir(), '.local', 'bin', WIDGET_COMMAND,
    ]);
}

function widgetPid() {
    try {
        const [ok, contents] = GLib.file_get_contents(WIDGET_PID_PATH);
        if (!ok)
            return 0;
        const pid = Number(new TextDecoder().decode(contents).trim());
        return Number.isInteger(pid) && pid > 1 ? pid : 0;
    } catch (_error) {
        return 0;
    }
}

function widgetIsRunning() {
    const pid = widgetPid();
    return pid > 0 && GLib.file_test(`/proc/${pid}`, GLib.FileTest.EXISTS);
}

const UsageIndicator = GObject.registerClass(
class UsageIndicator extends PanelMenu.Button {
    _init(extensionPath) {
        super._init(0.0, 'Claude and Codex Usage');
        this._refreshing = false;
        this._timerId = null;

        this._box = new St.BoxLayout({style_class: 'panel-status-menu-box'});
        this._icon = new St.Icon({
            gicon: Gio.icon_new_for_string(
                GLib.build_filenamev([extensionPath, 'codex-icon.png'])
            ),
            style_class: 'usage-panel-icon',
            icon_size: 16,
        });
        this._barBackground = new St.Widget({
            style_class: 'usage-panel-bar-background',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._barFill = new St.Widget({style_class: 'usage-panel-bar-fill'});
        this._barBackground.add_child(this._barFill);
        this._box.add_child(this._icon);
        this._box.add_child(this._barBackground);
        this.add_child(this._box);

        this._createMenu();
        this._refresh();
        this._timerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, REFRESH_SECONDS, () => {
            this._refresh();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _createMenu() {
        this._claudeSession = this._addUsageRow('Claude session');
        this._claudeWeekly = this._addUsageRow('Claude weekly');
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._codexSession = this._addUsageRow('Codex session');
        this._codexWeekly = this._addUsageRow('Codex weekly');
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._widgetAction = new PopupMenu.PopupMenuItem('Open themed widget');
        this._widgetAction.connect('activate', () => this._toggleWidget());
        this.menu.addMenuItem(this._widgetAction);

        const refresh = new PopupMenu.PopupMenuItem('Refresh');
        refresh.connect('activate', () => this._refresh());
        this.menu.addMenuItem(refresh);

        this._widgetAction.label.set_text(
            widgetIsRunning() ? 'Close themed widget' : 'Open themed widget'
        );

        this._updated = new PopupMenu.PopupMenuItem('Loading usage data…');
        this._updated.setSensitive(false);
        this.menu.addMenuItem(this._updated);
    }

    _addUsageRow(title) {
        const content = new St.BoxLayout({style_class: 'usage-menu-section', vertical: true});
        const header = new St.BoxLayout();
        const label = new St.Label({text: title, style_class: 'usage-menu-title'});
        const value = new St.Label({
            text: '…',
            style_class: 'usage-menu-value',
            x_expand: true,
            x_align: Clutter.ActorAlign.END,
        });
        header.add_child(label);
        header.add_child(value);
        content.add_child(header);

        const background = new St.Widget({style_class: 'usage-menu-bar-background'});
        const fill = new St.Widget({style_class: 'usage-menu-bar-fill'});
        background.add_child(fill);
        content.add_child(background);

        const item = new PopupMenu.PopupBaseMenuItem({reactive: false, can_focus: false});
        item.add_child(content);
        this.menu.addMenuItem(item);
        return {fill, item, value};
    }

    _refresh() {
        if (this._refreshing)
            return;
        this._refreshing = true;
        const command = widgetCommand();
        const process = Gio.Subprocess.new(
            [command, '--once', '--json'],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
        );
        process.communicate_utf8_async(null, null, (source, result) => {
            this._refreshing = false;
            try {
                const [, stdout] = source.communicate_utf8_finish(result);
                const data = JSON.parse(stdout);
                this._applyUsage(data);
            } catch (error) {
                this._updated.label.set_text(`Unable to refresh: ${error.message}`);
            }
        });
    }

    _applyUsage(data) {
        const claudeSession = percent(data.session_utilization);
        const claudeWeekly = percent(data.weekly_utilization);
        const codexSession = percent(data.codex_session_utilization);
        const codexWeekly = percent(data.codex_weekly_utilization);

        this._setUsageRow(this._claudeSession, claudeSession);
        this._setUsageRow(this._claudeWeekly, claudeWeekly);
        this._setUsageRow(this._codexSession, codexSession);
        this._setUsageRow(this._codexWeekly, codexWeekly);
        if (data.codex_available) {
            this._codexSession.item.show();
            this._codexWeekly.item.show();
        } else {
            this._codexSession.item.hide();
            this._codexWeekly.item.hide();
        }

        const maxUsage = Math.max(claudeSession, codexSession);
        this._barFill.set_width(Math.max(2, Math.round(maxUsage * 0.5)));
        this._updated.label.set_text(`Updated ${new Date().toLocaleTimeString()}`);
    }

    _setUsageRow(row, usage) {
        row.value.set_text(`${usage}%`);
        row.fill.set_width(Math.max(2, Math.round(usage * 2.1)));
    }

    _toggleWidget() {
        if (widgetIsRunning()) {
            Gio.Subprocess.new(['/bin/kill', '-TERM', String(widgetPid())], Gio.SubprocessFlags.NONE);
            this._widgetAction.label.set_text('Open themed widget');
            return;
        }
        Gio.Subprocess.new([widgetCommand(), '--detach'], Gio.SubprocessFlags.NONE);
        this._widgetAction.label.set_text('Close themed widget');
    }

    destroy() {
        if (this._timerId) {
            GLib.source_remove(this._timerId);
            this._timerId = null;
        }
        super.destroy();
    }
});

export default class ClaudeCodexUsageExtension extends Extension {
    enable() {
        this._indicator = new UsageIndicator(this.path);
        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
