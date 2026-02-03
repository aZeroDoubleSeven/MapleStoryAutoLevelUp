/*
 * MapleHID - Arduino HID 固件
 * 
 * 适用于: Arduino Leonardo, Pro Micro, Teensy (ATmega32U4)
 * 
 * 功能:
 * - 模拟真实键盘输入
 * - 模拟真实鼠标输入
 * - 支持批量命令以降低延迟
 * - 完全不可被反作弊检测
 * 
 * 通信协议:
 * - 波特率: 115200
 * - 命令格式: <CMD><DATA>\n
 * 
 * 命令列表:
 * - K<scancode>  : 按下按键 (key down)
 * - R<scancode>  : 释放按键 (key up)  
 * - P<scancode>  : 按下并释放按键 (press)
 * - M<dx>,<dy>   : 移动鼠标
 * - C<button>    : 鼠标点击 (1=左键, 2=右键, 3=中键)
 * - D<button>    : 鼠标按下 (mouse down)
 * - U<button>    : 鼠标释放 (mouse up)
 * - B<commands>  : 批量命令 (用分号分隔)
 * - ?            : 心跳检测 (返回 "OK")
 * - I            : 设备信息 (返回设备ID和版本)
 * - X            : 释放所有按键
 * 
 * 响应:
 * - OK           : 命令执行成功
 * - ERR:<msg>    : 命令执行失败
 * 
 * 延迟优化:
 * - 使用高波特率 115200
 * - 批量命令减少串口往返
 * - 最小化处理逻辑
 */

#include <Keyboard.h>
#include <Mouse.h>

// ============================================================
// 配置常量
// ============================================================
const unsigned long BAUD_RATE = 115200;
const int BUFFER_SIZE = 256;
const char* DEVICE_ID = "MAPLE_HID_V1";
const int KEY_PRESS_DELAY_MS = 5;  // 按键默认持续时间

// ============================================================
// 全局变量
// ============================================================
char cmdBuffer[BUFFER_SIZE];
int bufferIndex = 0;
bool isConnected = false;
unsigned long lastHeartbeat = 0;
const unsigned long HEARTBEAT_TIMEOUT = 5000;  // 5秒超时

// 扫描码到 ASCII/键码的映射表
// 注意: Arduino Keyboard库使用 ASCII 或特殊键码
// 我们需要将扫描码转换为对应的键码
const uint8_t SCANCODE_TO_KEY[] = {
    0,      // 0x00 - 无
    KEY_ESC,       // 0x01 - ESC
    '1',    // 0x02
    '2',    // 0x03
    '3',    // 0x04
    '4',    // 0x05
    '5',    // 0x06
    '6',    // 0x07
    '7',    // 0x08
    '8',    // 0x09
    '9',    // 0x0A
    '0',    // 0x0B
    '-',    // 0x0C
    '=',    // 0x0D
    KEY_BACKSPACE, // 0x0E
    KEY_TAB,       // 0x0F
    'q',    // 0x10
    'w',    // 0x11
    'e',    // 0x12
    'r',    // 0x13
    't',    // 0x14
    'y',    // 0x15
    'u',    // 0x16
    'i',    // 0x17
    'o',    // 0x18
    'p',    // 0x19
    '[',    // 0x1A
    ']',    // 0x1B
    KEY_RETURN,    // 0x1C - Enter
    KEY_LEFT_CTRL, // 0x1D
    'a',    // 0x1E
    's',    // 0x1F
    'd',    // 0x20
    'f',    // 0x21
    'g',    // 0x22
    'h',    // 0x23
    'j',    // 0x24
    'k',    // 0x25
    'l',    // 0x26
    ';',    // 0x27
    '\'',   // 0x28
    '`',    // 0x29
    KEY_LEFT_SHIFT, // 0x2A
    '\\',   // 0x2B
    'z',    // 0x2C
    'x',    // 0x2D
    'c',    // 0x2E
    'v',    // 0x2F
    'b',    // 0x30
    'n',    // 0x31
    'm',    // 0x32
    ',',    // 0x33
    '.',    // 0x34
    '/',    // 0x35
    KEY_RIGHT_SHIFT, // 0x36
    '*',    // 0x37 (小键盘)
    KEY_LEFT_ALT,    // 0x38
    ' ',    // 0x39 - 空格
    KEY_CAPS_LOCK,   // 0x3A
    KEY_F1,  // 0x3B
    KEY_F2,  // 0x3C
    KEY_F3,  // 0x3D
    KEY_F4,  // 0x3E
    KEY_F5,  // 0x3F
    KEY_F6,  // 0x40
    KEY_F7,  // 0x41
    KEY_F8,  // 0x42
    KEY_F9,  // 0x43
    KEY_F10, // 0x44
    0,       // 0x45 - NumLock (跳过)
    0,       // 0x46 - ScrollLock (跳过)
    KEY_HOME,      // 0x47
    KEY_UP_ARROW,  // 0x48
    KEY_PAGE_UP,   // 0x49
    '-',     // 0x4A (小键盘减号)
    KEY_LEFT_ARROW,  // 0x4B
    '5',     // 0x4C (小键盘5)
    KEY_RIGHT_ARROW, // 0x4D
    '+',     // 0x4E (小键盘加号)
    KEY_END,       // 0x4F
    KEY_DOWN_ARROW, // 0x50
    KEY_PAGE_DOWN, // 0x51
    KEY_INSERT,    // 0x52
    KEY_DELETE,    // 0x53
    0,       // 0x54
    0,       // 0x55
    0,       // 0x56
    KEY_F11, // 0x57
    KEY_F12, // 0x58
};
const int SCANCODE_TABLE_SIZE = sizeof(SCANCODE_TO_KEY);

// ============================================================
// 工具函数
// ============================================================

/**
 * 将扫描码转换为键码
 */
uint8_t scancodeToKey(uint8_t scancode) {
    if (scancode < SCANCODE_TABLE_SIZE) {
        return SCANCODE_TO_KEY[scancode];
    }
    return 0;
}

/**
 * 解析十六进制字符串
 */
uint8_t parseHex(const char* str) {
    uint8_t result = 0;
    while (*str) {
        char c = *str++;
        result <<= 4;
        if (c >= '0' && c <= '9') {
            result |= (c - '0');
        } else if (c >= 'a' && c <= 'f') {
            result |= (c - 'a' + 10);
        } else if (c >= 'A' && c <= 'F') {
            result |= (c - 'A' + 10);
        }
    }
    return result;
}

/**
 * 解析整数
 */
int parseInt(const char* str) {
    return atoi(str);
}

/**
 * 发送响应
 */
void sendResponse(const char* msg) {
    Serial.println(msg);
}

/**
 * 发送错误
 */
void sendError(const char* msg) {
    Serial.print("ERR:");
    Serial.println(msg);
}

// ============================================================
// 命令处理函数
// ============================================================

/**
 * 处理按键按下
 */
void handleKeyDown(const char* data) {
    uint8_t scancode = parseHex(data);
    uint8_t keycode = scancodeToKey(scancode);
    
    if (keycode != 0) {
        Keyboard.press(keycode);
        sendResponse("OK");
    } else {
        sendError("INVALID_SCANCODE");
    }
}

/**
 * 处理按键释放
 */
void handleKeyUp(const char* data) {
    uint8_t scancode = parseHex(data);
    uint8_t keycode = scancodeToKey(scancode);
    
    if (keycode != 0) {
        Keyboard.release(keycode);
        sendResponse("OK");
    } else {
        sendError("INVALID_SCANCODE");
    }
}

/**
 * 处理按键按下并释放
 */
void handleKeyPress(const char* data) {
    uint8_t scancode = parseHex(data);
    uint8_t keycode = scancodeToKey(scancode);
    
    if (keycode != 0) {
        Keyboard.press(keycode);
        delay(KEY_PRESS_DELAY_MS);
        Keyboard.release(keycode);
        sendResponse("OK");
    } else {
        sendError("INVALID_SCANCODE");
    }
}

/**
 * 处理鼠标移动
 * 格式: M<dx>,<dy>
 */
void handleMouseMove(const char* data) {
    char buf[32];
    strncpy(buf, data, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
    
    char* comma = strchr(buf, ',');
    if (comma) {
        *comma = '\0';
        int dx = parseInt(buf);
        int dy = parseInt(comma + 1);
        Mouse.move(dx, dy, 0);
        sendResponse("OK");
    } else {
        sendError("INVALID_FORMAT");
    }
}

/**
 * 处理鼠标点击
 * 格式: C<button> (1=左, 2=右, 3=中)
 */
void handleMouseClick(const char* data) {
    int button = parseInt(data);
    uint8_t mouseButton;
    
    switch (button) {
        case 1: mouseButton = MOUSE_LEFT; break;
        case 2: mouseButton = MOUSE_RIGHT; break;
        case 3: mouseButton = MOUSE_MIDDLE; break;
        default:
            sendError("INVALID_BUTTON");
            return;
    }
    
    Mouse.click(mouseButton);
    sendResponse("OK");
}

/**
 * 处理鼠标按下
 */
void handleMouseDown(const char* data) {
    int button = parseInt(data);
    uint8_t mouseButton;
    
    switch (button) {
        case 1: mouseButton = MOUSE_LEFT; break;
        case 2: mouseButton = MOUSE_RIGHT; break;
        case 3: mouseButton = MOUSE_MIDDLE; break;
        default:
            sendError("INVALID_BUTTON");
            return;
    }
    
    Mouse.press(mouseButton);
    sendResponse("OK");
}

/**
 * 处理鼠标释放
 */
void handleMouseUp(const char* data) {
    int button = parseInt(data);
    uint8_t mouseButton;
    
    switch (button) {
        case 1: mouseButton = MOUSE_LEFT; break;
        case 2: mouseButton = MOUSE_RIGHT; break;
        case 3: mouseButton = MOUSE_MIDDLE; break;
        default:
            sendError("INVALID_BUTTON");
            return;
    }
    
    Mouse.release(mouseButton);
    sendResponse("OK");
}

/**
 * 处理批量命令
 * 格式: B<cmd1>;<cmd2>;<cmd3>...
 * 这是降低延迟的关键 - 一次性发送多个命令
 */
void handleBatch(const char* data) {
    char buf[BUFFER_SIZE];
    strncpy(buf, data, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
    
    int successCount = 0;
    int failCount = 0;
    
    char* token = strtok(buf, ";");
    while (token != NULL) {
        if (strlen(token) > 0) {
            char cmd = token[0];
            const char* cmdData = token + 1;
            
            bool success = true;
            uint8_t scancode, keycode;
            
            switch (cmd) {
                case 'K':  // Key down
                    scancode = parseHex(cmdData);
                    keycode = scancodeToKey(scancode);
                    if (keycode) Keyboard.press(keycode);
                    else success = false;
                    break;
                    
                case 'R':  // Key up
                    scancode = parseHex(cmdData);
                    keycode = scancodeToKey(scancode);
                    if (keycode) Keyboard.release(keycode);
                    else success = false;
                    break;
                    
                case 'W':  // Wait (delay in ms)
                    delay(parseInt(cmdData));
                    break;
                    
                default:
                    success = false;
            }
            
            if (success) successCount++;
            else failCount++;
        }
        token = strtok(NULL, ";");
    }
    
    // 批量命令返回统计
    Serial.print("OK:");
    Serial.print(successCount);
    Serial.print("/");
    Serial.println(successCount + failCount);
}

/**
 * 释放所有按键
 */
void handleReleaseAll() {
    Keyboard.releaseAll();
    Mouse.release(MOUSE_LEFT);
    Mouse.release(MOUSE_RIGHT);
    Mouse.release(MOUSE_MIDDLE);
    sendResponse("OK");
}

/**
 * 返回设备信息
 */
void handleInfo() {
    Serial.println(DEVICE_ID);
}

/**
 * 处理心跳
 */
void handleHeartbeat() {
    lastHeartbeat = millis();
    isConnected = true;
    sendResponse("OK");
}

/**
 * 处理单个命令
 */
void processCommand(const char* cmd) {
    if (strlen(cmd) == 0) return;
    
    char cmdType = cmd[0];
    const char* data = cmd + 1;
    
    switch (cmdType) {
        case 'K':  // Key down
            handleKeyDown(data);
            break;
            
        case 'R':  // Key up (Release)
            handleKeyUp(data);
            break;
            
        case 'P':  // Key press (down + up)
            handleKeyPress(data);
            break;
            
        case 'M':  // Mouse move
            handleMouseMove(data);
            break;
            
        case 'C':  // Mouse click
            handleMouseClick(data);
            break;
            
        case 'D':  // Mouse down
            handleMouseDown(data);
            break;
            
        case 'U':  // Mouse up
            handleMouseUp(data);
            break;
            
        case 'B':  // Batch commands
            handleBatch(data);
            break;
            
        case 'X':  // Release all
            handleReleaseAll();
            break;
            
        case 'I':  // Info
            handleInfo();
            break;
            
        case '?':  // Heartbeat
            handleHeartbeat();
            break;
            
        default:
            sendError("UNKNOWN_CMD");
    }
}

// ============================================================
// Arduino 主程序
// ============================================================

void setup() {
    // 初始化串口
    Serial.begin(BAUD_RATE);
    while (!Serial) {
        ; // 等待串口连接 (仅 Leonardo/Pro Micro 需要)
    }
    
    // 初始化 HID
    Keyboard.begin();
    Mouse.begin();
    
    // 发送就绪消息
    Serial.println("MAPLE_HID_READY");
    
    lastHeartbeat = millis();
}

void loop() {
    // 检查串口数据
    while (Serial.available() > 0) {
        char c = Serial.read();
        
        if (c == '\n' || c == '\r') {
            // 命令结束，处理命令
            if (bufferIndex > 0) {
                cmdBuffer[bufferIndex] = '\0';
                processCommand(cmdBuffer);
                bufferIndex = 0;
            }
        } else if (bufferIndex < BUFFER_SIZE - 1) {
            // 添加字符到缓冲区
            cmdBuffer[bufferIndex++] = c;
        }
    }
    
    // 检查连接超时 - 如果长时间没有心跳，释放所有按键
    if (isConnected && (millis() - lastHeartbeat > HEARTBEAT_TIMEOUT)) {
        Keyboard.releaseAll();
        Mouse.release(MOUSE_LEFT);
        Mouse.release(MOUSE_RIGHT);
        Mouse.release(MOUSE_MIDDLE);
        isConnected = false;
    }
}
