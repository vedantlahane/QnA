interface SpeechRecognitionAlternative {
  readonly transcript: string;
  readonly confidence: number;
}

interface SpeechRecognitionResult extends ArrayLike<SpeechRecognitionAlternative> {
  readonly isFinal: boolean;
}

interface SpeechRecognitionResultList extends ArrayLike<SpeechRecognitionResult> {}

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

interface SpeechRecognitionWindow {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
}

declare var webkitSpeechRecognition: SpeechRecognitionConstructor;

declare global {
  interface Window extends SpeechRecognitionWindow {}
}
