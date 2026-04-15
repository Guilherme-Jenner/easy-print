# 📸 EasyPrint

> A fast, stealthy, and Wayland-optimized screenshot tool with native editing capabilities.

**EasyPrint** is a system utility designed specifically for modern Linux environments (such as Pop!_OS and Ubuntu). It runs silently in the background as a daemon and features a custom rendering engine with geometry bypass, ensuring transparent overlays and instant editing even under Wayland's strict security restrictions.

## ✨ Key Features

* 🚀 **Client-Server Architecture (IPC):** Runs in the background consuming near 0% CPU and is triggered instantly via command line.
* 🛡️ **Wayland Optimized:** Bypasses modern compositor blocks, allowing transparent screen overlays without black/gray screen artifacts.
* ✏️ **Built-in Vector Editor:** Draw arrows (with applied trigonometry), rectangles, and lines directly on the screenshot before saving.
* ↩️ **Action History:** Made a mistake? Just press `Ctrl+Z` to undo your last annotation.
* 🥷 **Stealth Mode:** Option to hide the system tray icon, leaving the tool running 100% invisibly, controlled solely by keyboard shortcuts.
* 📋 **Fast Export:** Save directly to disk (`.png` files) or copy the edited image straight to your Clipboard.

---

## 📦 Installation (Recommended)

The easiest way to install EasyPrint is by using the pre-compiled Debian package.

1. Go to the [Releases](../../releases) tab on GitHub and download the latest version (`easy-print_X.X.X_amd64.deb`).
2. Open the terminal in your download folder and run:

    ```bash
    sudo apt install ./easy-print_1.0.0_amd64.deb
    ```

> **Note:** The daemon will start automatically after restarting the computer, or it can be started manually by executing the command `easy-print` via the terminal.

---

## 🚀 Execution & Keyboard Shortcut (How to Use)

EasyPrint operates in two parts: a silent background daemon and a lightning-fast trigger command.

### 1. The Background Daemon
After installation, the daemon will automatically start on your next system boot. To use it immediately without restarting, launch **EasyPrint** from your application menu or type `easy-print` in the terminal. Once running, it sits silently in your system tray awaiting your command without consuming resources.

### 2. The Screen Capture Trigger (Custom Shortcut)
To actually take a screenshot, you need to send a signal to the daemon. **The best way to use EasyPrint is by setting up a custom keyboard shortcut in your system.**

1. Open your Linux **Settings** -> **Keyboard** -> **Keyboard Shortcuts** -> **View and Customize Shortcuts** -> **Custom Shortcuts**.
2. Add a new shortcut with the following details:
   * **Name:** Take Screenshot (EasyPrint)
   * **Command:** `easy-print --trigger`
   * **Shortcut:** `Super + Shift + S` (or any other combination you prefer).

Now, whenever you press your custom shortcut, the `easy-print --trigger` command will instantly wake the daemon, freeze the screen, and open the drawing tools!

---

## 🛠️ Building from Source

If you wish to modify the code and compile your own version, follow these steps:

**Prerequisites:**
* Python 3 installed
* Virtual Environment (venv) configured

**1. Clone the repository and install dependencies:**
    ```bash
    git clone [https://github.com/Guilherme-Jenner/easy-print.git](https://github.com/Guilherme-Jenner/easy-print.git)
    cd easy-print
    source venv/bin/activate
    pip install PySide6 pyinstaller
    ```

**2. Generate the native executable:**
    ```bash
    pyinstaller --name easy-print --onefile --windowed --clean main.py
    ```

**3. Package in Debian format:**
Copy the generated binary from the `dist/` folder to the `.deb` directory structure (`usr/bin/`) and run:
    ```bash
    dpkg-deb --build easy-print_1.0.0_amd64
    ```

---

## 🤝 Contributing

Contributions are very welcome! If you find a bug or have an idea for a new editor tool, feel free to open an Issue or submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.