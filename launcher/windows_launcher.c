#define UNICODE
#define _UNICODE
#include <windows.h>
#include <wchar.h>
#include <stdio.h>

static int failure(const wchar_t *message) {
    MessageBoxW(NULL, message, L"ATP ROA Studio", MB_OK | MB_ICONERROR);
    return 1;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR arguments, int show) {
    wchar_t root[32768], python[32768], script[32768], command[32768];
    wchar_t old_path[32768], new_path[32768];
    DWORD length = GetModuleFileNameW(NULL, root, 32768);
    if (!length || length >= 32768)
        return failure(L"Cannot locate the application folder. / アプリのフォルダーが見つかりません。");
    wchar_t *separator = wcsrchr(root, L'\\');
    if (!separator) return failure(L"Cannot locate the application folder.");
    *separator = L'\0';
    if (wcslen(root) > 8000)
        return failure(L"Move the application to a shorter folder path. / 短いフォルダーパスに移動してください。");
    swprintf(python, 32768, L"%ls\\python\\pythonw.exe", root);
    swprintf(script, 32768, L"%ls\\launch.py", root);
    if (GetFileAttributesW(python) == INVALID_FILE_ATTRIBUTES ||
        GetFileAttributesW(script) == INVALID_FILE_ATTRIBUTES)
        return failure(L"Extract the entire ZIP before starting. Keep this executable inside the application folder.\n\nZIP全体を展開してください。この実行ファイルをアプリのフォルダー内に置いてください。");
    DWORD env_length = GetEnvironmentVariableW(L"PATH", old_path, 32768);
    if (!env_length) old_path[0] = L'\0';
    if (env_length >= 32768 || 2 * wcslen(root) + wcslen(old_path) + 40 >= 32768)
        return failure(L"The Windows PATH is too long. / WindowsのPATHが長すぎます。");
    swprintf(new_path, 32768, L"%ls\\runtime\\jre\\bin;%ls\\python;%ls", root, root, old_path);
    SetEnvironmentVariableW(L"PATH", new_path);
    SetEnvironmentVariableW(L"PYTHONUTF8", L"1");
    SetEnvironmentVariableW(L"ATP_STUDIO_DESKTOP", L"1");
    if (wcslen(python) + wcslen(script) + wcslen(arguments) + 10 >= 32768)
        return failure(L"The file path is too long. / ファイルのパスが長すぎます。");
    swprintf(command, 32768, L"\"%ls\" \"%ls\" %ls", python, script, arguments);
    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION process = {0};
    startup.cb = sizeof(startup);
    if (!CreateProcessW(python, command, NULL, NULL, FALSE, CREATE_NO_WINDOW,
                        NULL, root, &startup, &process)) {
        wchar_t message[1024];
        swprintf(message, 1024,
                 L"Could not start ATP ROA Studio (Windows error %lu).\nExtract the complete ZIP again and try again.\n\n起動できませんでした。ZIP全体を再展開してお試しください。", GetLastError());
        return failure(message);
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return 0;
}
