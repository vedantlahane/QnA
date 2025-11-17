interface SpeechRecognitionAlternative {
  readonly transcript: string;
  readonly confidence: number;
}

interface SpeechRecognitionResult extends ArrayLike<SpeechRecognitionAlternative> {
  readonly isFinal: boolean;
}

interface SpeechRecognitionResultList extends ArrayLike<SpeechRecognitionResult> {
  item(index: number): SpeechRecognitionResult | null;
}

interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultList;
}

type SpeechRecognitionCallback = ((event: Event) => void) | null;
type SpeechRecognitionResultCallback = ((event: SpeechRecognitionEvent) => void) | null;

interface SpeechRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onstart: SpeechRecognitionCallback;
  onend: SpeechRecognitionCallback;
  onerror: SpeechRecognitionCallback;
  onresult: SpeechRecognitionResultCallback;
  start(): void;
  stop(): void;
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognition;
}

type SpeechRecognitionWindow = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
};

interface Window {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
}

declare const webkitSpeechRecognition: SpeechRecognitionConstructor;
