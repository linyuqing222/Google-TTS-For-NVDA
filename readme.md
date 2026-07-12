# Google TTS For NVDA

An NVDA screen reader synthesizer add-on that uses Google's WebAssembly (WASM) Text-to-Speech engine locally through a supported browser runtime (Microsoft Edge or Google Chrome) to provide high-quality, natural-sounding voices offline.

This project was created to make Google's high-quality local WebAssembly Text-to-Speech engine usable as a practical, everyday NVDA synthesizer on Windows computers.

*This add-on is co-developed by [Nguyen Anh Duc](https://github.com/nguyenanhduc09), [Dao Duc Trung](https://github.com/daoductrung) and [Pham Hung Vuong](https://github.com/phamhungvuong302).*

---

## Current Status

This add-on is currently being actively maintained and developed by Nguyen Anh Duc, Dao Duc Trung and Pham Hung Vuong. Version 0.3 significantly improves several everyday speech paths, though browser runtime, WASM, cache, and engine behavior can still affect the final result:
* Voice package startup is improved because the add-on prepares the currently selected package instead of broadly warming multiple packages.
* Long text and UI speech handling is improved with more careful background segmentation, so speech can often begin sooner while keeping spoken output more natural.
* Audio balance and harshness are improved across voice packages with dynamic gain control and limiting, reducing the chance of clipping or distorted sound.
* SeaNet voice packages use post-synthesis artificial rate processing at higher speeds to preserve quality better; this can increase CPU usage when reading quickly.

We highly welcome and appreciate any feedback from the community to help us improve!

---

## Features

* **Comprehensive Voice Support**: Supports all languages and voices available in WasmTtsEngine. This includes Chrome OS packages (optimized for frequent use and high-speed screen reading) and Google Natural packages (designed for higher quality, standard text reading).
* **100% Offline Speech**: Speech is rendered locally via a supported headless browser runtime (Microsoft Edge or Google Chrome).
* **Low Latency**: Uses current-package warm-up and advanced background text segmentation to improve speech responsiveness.
* **Volatile Audio Cache**: In-memory cache for short phrases (under 5000 characters) to optimize repeated announcements safely.
* **Voice Manager**: Easily browse, filter by language, download, or remove voice packages in batches using a multi-select checkbox interface. Also includes an **Open voice packages folder** button to inspect storage locations.
* **Background Operations**: Non-blocking downloads and removals on background threads.
* **Accessible Shortcut**: Press **`NVDA+Ctrl+Shift+G`** to open the Voice Manager instantly.
* **Browser Runtime Selection**: Choose between Microsoft Edge and Google Chrome as the underlying engine directly from the NVDA settings panel.

---

## Requirements

* **NVDA**: Version 2024.1 or newer.
* **Browser runtime**: Microsoft Edge or Google Chrome must be present on the system. The add-on will search common paths or check your registry automatically. You can also specify a custom path using the `EDGE_PATH` or `CHROME_PATH` environment variable.

---

## Installation & First Run

1. Download the latest `.nvda-addon` package from the [Releases](https://github.com/nguyenanhduc09/Google-TTS-For-NVDA/releases) page.
2. Open the package (or use NVDA's Add-on Store -> Install from external source) and follow the prompts to install it.
3. Upon first selecting **Google TTS For NVDA** as your synthesizer, if no voice packages are installed, NVDA will prompt you indicating that no Google TTS For NVDA voices are installed. Press **OK** to open Google TTS Voice Manager and download a voice package, or press **Cancel** to keep using your current synthesizer.
4. Alternatively, you can also press **`NVDA+Ctrl+Shift+G`** or go to **NVDA Menu -> Tools -> Google TTS Voice Manager...** at any time to manage your voice packages.
5. In Google TTS Voice Manager, you can use the **Filter by language** dropdown to quickly find voices for your language, check the boxes next to the voice packages you want, and click **Download checked voice packages**.

---

## Configuration Settings

### Synthesizer Settings

The synthesizer supports the standard NVDA Speech settings ring:
* **Voice**: Choose from your installed speaker/language voice packages.
* **Rate**: Speech rate. Non-SeaNet packages use the browser runtime rate path; SeaNet packages may use post-synthesis artificial rate processing at higher speeds.
* **Rate Boost**: Enable to double the computed speech rate for fast reading. High-speed SeaNet speech may use more CPU because the add-on processes generated audio after synthesis.
* **Pitch**: Speech pitch adjustment.
* **Volume**: Speech volume (maps to the browser runtime's 0.0 - 1.0 volume range).

### Browser Runtime Settings

The add-on includes a custom settings panel under **NVDA Settings (NVDA Menu -> Preferences -> Settings) -> Google TTS For NVDA**:
* **Browser runtime**: Select which browser runtime to use (Microsoft Edge or Google Chrome). The panel shows the availability status of each browser on your system.

---

## Build Instructions (For Advanced Users)

To package the add-on yourself:

1. Clone this repository using `git clone https://github.com/nguyenanhduc09/Google-TTS-For-NVDA.git` and navigate to the directory.
2. Make sure you have **Python** and **Node.js** installed on your system.
3. Run the automated build script:

```bat
build.bat
```

The build script reads the version from `googleTtsForNvda/manifest.ini`, builds all add-on locales non-interactively, checks Python and JavaScript syntax, verifies that no `.zvoice` voice packages are inside the source tree, removes generated `__pycache__` folders, and packages the add-on.

The verified `.nvda-addon` package will be created in the `dist/` directory, with a name like:

```text
dist/googleTtsForNvda-0.3.nvda-addon
```

---

## Translation

We warmly welcome translations for new languages or updates to existing ones!

If you would like to translate this add-on into your local language:
* Read the detailed translation guide in [TRANSLATING.md](TRANSLATING.md) to understand the layout, workflow, and how to use translation tools such as Poedit.
* Use the helper script `build_i18n.py` to validate or build your translation files:
  * Running `python build_i18n.py` opens an interactive menu to guide you.
  * Running `python build_i18n.py --check --all-languages` validates all existing translations.
  * Running `python build_i18n.py --all-languages` compiles and updates translation files for all locales.

---

## Contributing

We strongly welcome contributions from other developers! If you have ideas, bug fixes, or improvements, please feel free to open an issue or submit a pull request.

---

## Contact

If you have any questions, feedback, or need support, feel free to reach out to us via email or Telegram:
* **Nguyen Anh Duc**: [ducna1803@gmail.com](mailto:ducna1803@gmail.com) | Telegram: [t.me/anhduc1803](https://t.me/anhduc1803)
* **Dao Duc Trung**: [trung@ddt.one](mailto:trung@ddt.one) | Telegram: [t.me/Daoductrung](https://t.me/Daoductrung)
* **Pham Hung Vuong**: [hungvuong106206@gmail.com](mailto:hungvuong106206@gmail.com) | Telegram: [t.me/phamhungvuong302](https://t.me/phamhungvuong302)
