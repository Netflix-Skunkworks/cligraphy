@0xcbbea7cb6eb29a56;

struct Session {
  username      @0  :Text;
  timestamp     @1  :UInt64;
  windowSize    @2  :WindowSize;
  environment   @3  :List(EnvVar);
}

struct WindowSize {
  columns       @0  :UInt16;
  lines         @1  :UInt16;
}

struct EnvVar {
    name        @0  :Text;
    value       @1  :Text;
}

struct Event {
    timecode    @0  :Float32;
    type        @1  :Type;

    union {
        data        @2  :Text;
        status      @3  :UInt16;
        windowSize  @4  :WindowSize;
    }

    enum Type {
        userInput       @0;
        ptyInput        @1;
        sessionEnd      @2;
        windowResized   @3;
    }
}
