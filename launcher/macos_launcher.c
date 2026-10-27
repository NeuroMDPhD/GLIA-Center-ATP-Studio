#include <CoreFoundation/CoreFoundation.h>
#include <mach-o/dyld.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    char executable[PATH_MAX], root[PATH_MAX], python[PATH_MAX], script[PATH_MAX];
    uint32_t size = sizeof(executable);
    if (_NSGetExecutablePath(executable, &size) || !realpath(executable, root)) return 1;
    for (int i = 0; i < 4; i++) {
        char *slash = strrchr(root, '/');
        if (!slash) return 1;
        *slash = '\0';
    }
    snprintf(python, sizeof(python), "%s/.venv/bin/python", root);
    snprintf(script, sizeof(script), "%s/launch.py", root);
    if (access(python, X_OK) == 0 && access(script, R_OK) == 0) {
        char **arguments = calloc((size_t)argc + 2, sizeof(char *));
        if (arguments) {
            arguments[0] = python; arguments[1] = script;
            for (int i = 1; i < argc; i++) arguments[i + 1] = argv[i];
            setenv("ATP_STUDIO_DESKTOP", "1", 1);
            setenv("PYTHONUTF8", "1", 1);
            chdir(root);
            execv(python, arguments);
            free(arguments);
        }
    }
    CFUserNotificationDisplayAlert(0, kCFUserNotificationStopAlertLevel, NULL, NULL, NULL,
        CFSTR("GLIA Center ATP Studio"),
        CFSTR("Keep this app beside launch.py and the .venv folder.\nこのアプリをlaunch.pyと.venvフォルダーと同じ場所に置いてください。"),
        CFSTR("OK"), NULL, NULL, NULL);
    return 1;
}
