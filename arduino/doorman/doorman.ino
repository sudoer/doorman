
// Boarduino note -- use Duemilanove and USBtinyISP

#define HEARTBEAT 13

#define BUFSIZE 40
static char buffer[BUFSIZE+1];
static int bufposn=0;
#define OUTSIZE 40
static char out[OUTSIZE+1];

void command() {
  Serial.println("");
  if (!strcmp(buffer,"hello")) {
    Serial.println("*HI");
    return;
  }
  if (strlen(buffer)==0) return;
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
      switch (buffer[posn]) {
        case '?': {
          pinMode(pin,INPUT);
          int val=digitalRead(pin);
          sprintf(out,"*d%d=%d",pin,val);
          Serial.println(out);
          return;
        }
        case '=': {
          posn++;
          if ((buffer[posn]>='0')&&(buffer[posn]<='9')) {
            int val=buffer[posn]-'0';
            posn++;
            pinMode(pin,OUTPUT);
            digitalWrite(pin,val);
            sprintf(out,"*d%d=%d",pin,val);
            Serial.println(out);
            return;
          }
          break;
        }
      }
    }
  }
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
      switch (buffer[posn]) {
        case '?': {
          int val=analogRead(pin);
          sprintf(out,"*a%d=%d",pin,val);
          Serial.println(out);
          return;
        }
      }
    }
  }
  Serial.println("???");
}

void prompt() {
  Serial.print(">");
}

void setup() {
  pinMode(HEARTBEAT,OUTPUT);
  Serial.begin(9600);
  prompt();
}

void loop() {
  // process serial data
  while (Serial.available() > 0) {
    char in = Serial.read();
    if ((in=='\n') || (in=='\r')) {
      command();
      prompt();
      bufposn = 0;
      buffer[bufposn] = 0;
    } else if (in==8) {
      if (bufposn>0) {
        bufposn--;
        buffer[bufposn] = 0;
        sprintf(out,"%c %c",8,8);
        Serial.print(out);
      }
    } else if ((in>=32)&&(in<=127)) {
      if (bufposn<BUFSIZE) { 
        Serial.print(in);
        buffer[bufposn++] = in;
        buffer[bufposn] = 0;
      }
    }
  }    
  // blink lights
  static int blink=0;
  if (blink++ > 1000) {
     int led=digitalRead(HEARTBEAT);
     digitalWrite(HEARTBEAT,led?0:1);
     blink=0;
  }
  // sleep
  delay(1);
}


