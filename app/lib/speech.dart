// 통화 자막용 네이티브 받아쓰기(app-front/README.md "호스트 계약" speechStart·speechStop, app-front backlog 04).
// - WebView에는 Web Speech API가 없어 speech_to_text(Android 음성 인식 서비스, iOS Apple 음성 인식)로 받아쓴다.
// - 플랫폼 인식기는 말이 끊기면 스스로 멈춘다. stop()이 불릴 때까지 다시 켠다.
// - 받아쓴 글은 onText로만 넘기고 로그에 찍지 않는다. 오류 기록은 오류 이름만 남긴다.

import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:speech_to_text/speech_recognition_error.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';

import 'bridge.dart';

/// 인식기가 멈춘 뒤 다시 켜기까지 기다리는 시간. 웹의 SPEECH_RESTART_MS와 같다
const Duration speechRestartDelay = Duration(milliseconds: 300);

/// 말이 이만큼 끊기면 한 문장으로 확정한다. iOS는 이 값이 없으면 1분 동안 한 문장으로 이어 붙인다
const Duration speechPauseFor = Duration(seconds: 3);

/// 한 번 켜서 듣는 최대 시간. iOS 인식기는 약 1분이 한도다
const Duration speechListenFor = Duration(seconds: 55);

class NativeSpeech {
  NativeSpeech({required this.onText, required this.onError, required this.log});

  /// 말하는 중(isFinal: false)과 확정 문장(isFinal: true)
  final void Function(String text, bool isFinal) onText;

  /// 받아쓰기를 계속할 수 없다. 이미 껐다
  final void Function(SpeechErrorKind kind) onError;
  final void Function(String text) log;

  final SpeechToText _stt = SpeechToText();
  bool _initialized = false;

  /// start·stop마다 올린다. 앞 세션의 늦은 결과·상태는 버린다
  int _session = 0;
  String? _lang;
  Timer? _restartTimer;
  int _errors = 0;

  bool get active => _lang != null;

  Future<void> start(String lang) async {
    final session = ++_session;
    _lang = lang;
    _errors = 0;
    _restartTimer?.cancel();
    if (_stt.isListening) await _stt.cancel();
    if (!_initialized) {
      bool ok;
      try {
        ok = await _stt.initialize(
          onError: _onError,
          onStatus: _onStatus,
          // 블루투스 헤드셋 연결 권한(BLUETOOTH_CONNECT)을 요구하지 않게 한다
          options: [SpeechToText.androidNoBluetooth],
        );
      } on Object catch (e) {
        log('speech 초기화 실패(${e.runtimeType})');
        ok = false;
      }
      if (session != _session) return;
      if (!ok) {
        _fail(await _stt.hasPermission ? SpeechErrorKind.unsupported : SpeechErrorKind.denied);
        return;
      }
      _initialized = true;
    }
    await _listen(session);
  }

  /// 끄고 듣던 말은 버린다
  void stop() {
    _session++;
    _lang = null;
    _restartTimer?.cancel();
    _restartTimer = null;
    if (_initialized) _stt.cancel();
  }

  Future<void> _listen(int session) async {
    final lang = _lang;
    if (lang == null || session != _session) return;
    try {
      await _stt.listen(
        onResult: (result) => _onResult(session, result),
        listenOptions: SpeechListenOptions(
          localeId: lang,
          partialResults: true,
          listenMode: ListenMode.dictation,
          cancelOnError: false,
          pauseFor: speechPauseFor,
          listenFor: speechListenFor,
        ),
      );
    } on Object catch (e) {
      log('speech listen 실패(${e.runtimeType})');
      _scheduleRestart(session);
    }
  }

  void _onResult(int session, SpeechRecognitionResult result) {
    if (session != _session) return;
    _errors = 0;
    onText(result.recognizedWords, result.finalResult);
  }

  void _onStatus(String status) {
    if (!active) return;
    // done: 이번 듣기가 끝났다(말 끊김·시간 한도·오류 뒤). stop()을 부를 때까지 다시 켠다
    if (status == SpeechToText.doneStatus) _scheduleRestart(_session);
  }

  void _onError(SpeechRecognitionError error) {
    if (!active) return;
    if (speechErrorCounts(error.errorMsg)) _errors++;
    final kind = speechErrorKind(error.errorMsg, errorsInRow: _errors);
    log('speech 오류(${error.errorMsg})${kind == null ? '' : ' → 받아쓰기 끔'}');
    if (kind != null) {
      _fail(kind);
    } else {
      _scheduleRestart(_session);
    }
  }

  void _scheduleRestart(int session) {
    if (session != _session || !active) return;
    _restartTimer?.cancel();
    _restartTimer = Timer(speechRestartDelay, () {
      _restartTimer = null;
      if (session != _session || _stt.isListening) return;
      _listen(session);
    });
  }

  void _fail(SpeechErrorKind kind) {
    stop();
    onError(kind);
  }

  void dispose() => stop();
}

/// 기기에서 받아쓰기를 이을 수 있는가. 인식기·권한은 켜 봐야 알므로 플랫폼만 본다
bool get speechPlatformSupported => !kIsWeb && (Platform.isAndroid || Platform.isIOS);
