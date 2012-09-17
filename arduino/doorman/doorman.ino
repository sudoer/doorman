// Boarduino note -- use Duemilanove and USBtinyISP
// Arduino Nano note -- use ??? and ???

// this output pin blinks while we're running
#define HEARTBEAT 0

#define BUFSIZE 40
static char buffer[BUFSIZE+1];
static int bufposn=0;
#define OUTSIZE 40
static char out[OUTSIZE+1];
static int echo=1;

//------------------------------------------------------------------------------

void prompt() {
    Serial.print(">");
}

//------------------------------------------------------------------------------

void response() {
    Serial.print("*");
}

//------------------------------------------------------------------------------

// interpret a serial command
void command() {
    // valid commands are:
    // hi : responds with "hello"
    // e+ : echo on
    // e- : echo off
    // a5? : reads analog input #5
    // d2? : reads digital input #2
    // d7=1 : turns on digital output #7

    if (strlen(buffer)==0) return;

    // COMMAND - HELLO
    if (!strcmp(buffer,"hi")) {
        response();
        Serial.println("hello");
        return;
    }
    // COMMAND - ECHO
    if (buffer[0]=='e') {
        // on (+) or off (-)
        switch (buffer[1]) {
            case '+':
                echo=1;
                response();
                Serial.println("e+");
                return;
            case '-':
                echo=0;
                response();
                Serial.println("e-");
                return;
        }
    }
    // COMMAND - DIGITAL
    if (buffer[0]=='d') {
        int posn=1;
        int pin;
        // first numeric digit
        if ((buffer[posn]>='0')&&(buffer[posn]<='9')) {
            pin=buffer[posn]-'0';
            posn++;
            // optional second numeric digit
            if ((buffer[posn]>='0')&&(buffer[posn]<='9')) {
                pin=pin*10+(buffer[posn]-'0');
                posn++;
            }
            // read (?) or write (=)
            switch (buffer[posn]) {
                case '?': {
                    response();
                    pinMode(pin,INPUT);
                    int val=digitalRead(pin);
                    sprintf(out,"d%d=%d",pin,val);
                    Serial.println(out);
                    return;
                }
                case '=': {
                    posn++;
                    // numeric value to write, 0 or 1
                    if ((buffer[posn]>='0')&&(buffer[posn]<='1')) {
                        response();
                        int val=buffer[posn]-'0';
                        posn++;
                        pinMode(pin,OUTPUT);
                        digitalWrite(pin,val);
                        sprintf(out,"d%d=%d",pin,val);
                        Serial.println(out);
                        return;
                    }
                    break;
                }
            }
        }
    }
    // COMMAND - ANALOG
    if (buffer[0]=='a') {
        int posn=1;
        int pin;
        // first numeric digit
        if ((buffer[posn]>='0')&&(buffer[posn]<='9')) {
            pin=buffer[posn]-'0';
            posn++;
            // optional second numeric digit
            if ((buffer[posn]>='0')&&(buffer[posn]<='9')) {
                pin=pin*10+(buffer[posn]-'0');
                posn++;
            }
            // read (?) - note that we can not write (=) to analog ports
            switch (buffer[posn]) {
                case '?': {
                    response();
                    int val=analogRead(pin);
                    sprintf(out,"a%d=%d",pin,val);
                    Serial.println(out);
                    return;
                }
            }
        }
    }
    // command not understood
    Serial.println("???");
}

//------------------------------------------------------------------------------

void setup() {
    pinMode(HEARTBEAT,OUTPUT);
    Serial.begin(9600);
    if (echo) prompt();
}

//------------------------------------------------------------------------------

void loop() {
    // process all serial data available
    while (Serial.available() > 0) {
        char in = Serial.read();
        // look for end of line
        if ((in=='\n') || (in=='\r')) {
            if (echo) Serial.println("");
            command();
            if (echo) prompt();
            bufposn = 0;
            buffer[bufposn] = 0;
        }
        // backspace
        else if (in==8) {
            if (bufposn>0) {
                // trim input buffer
                bufposn--;
                buffer[bufposn] = 0;
                // erase old character
                sprintf(out,"%c %c",8,8);
                if (echo) Serial.print(out);
            }
        }
        // printable ASCII character
        else if ((in>=32)&&(in<=127)) {
            if (bufposn<BUFSIZE) { 
                buffer[bufposn++] = in;
                buffer[bufposn] = 0;
                if (echo) Serial.print(in);
            }
        }
    }
    // blink the heartbeat light
    // every 1000 times through this loop
    static int blink=0;
    if (blink++ > 1000) {
        int led=digitalRead(HEARTBEAT);
        digitalWrite(HEARTBEAT,led?0:1);
        blink=0;
    }
    // sleep
    delay(1);
}

//------------------------------------------------------------------------------


