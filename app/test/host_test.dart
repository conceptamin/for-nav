import 'package:flutter/widgets.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:for_nav/bridge.dart';
import 'package:for_nav/navigation.dart';
import 'package:for_nav/push.dart';

void main() {
  final app = Uri.parse('http://10.0.2.2:5181');

  group('classifyNavigation', () {
    NavigationTarget main(String url) => classifyNavigation(url, app, isMainFrame: true);

    test('앱 출처 안은 WebView에서 연다', () {
      expect(main('http://10.0.2.2:5181/__host'), NavigationTarget.app);
      expect(main('about:blank'), NavigationTarget.app);
    });

    test('전화·문자·메일과 다른 사이트는 외부로 연다', () {
      expect(main('tel:119'), NavigationTarget.external);
      expect(main('sms:01000000000'), NavigationTarget.external);
      expect(main('mailto:a@example.com'), NavigationTarget.external);
      expect(main('https://map.kakao.com/link/search/울산'), NavigationTarget.external);
      // 포트·scheme이 다르면 다른 출처다
      expect(main('http://10.0.2.2:8000/api'), NavigationTarget.external);
      expect(main('https://10.0.2.2:5181/'), NavigationTarget.external);
    });

    test('앱 밖 하위 프레임은 막기만 한다', () {
      expect(classifyNavigation('https://example.com', app, isMainFrame: false), NavigationTarget.blocked);
      expect(classifyNavigation('http://10.0.2.2:5181/x', app, isMainFrame: false), NavigationTarget.app);
    });
  });

  group('bridge', () {
    test('type이 없거나 JSON이 아니면 무시한다', () {
      expect(parseMessage('not json'), isNull);
      expect(parseMessage('[1]'), isNull);
      expect(parseMessage('{"protocol":1}'), isNull);
      expect(parseMessage('{"protocol":1,"type":"ready","path":"/"}')?['type'], 'ready');
    });

    test('init은 계약의 필드를 모두 담는다', () {
      final msg = initMessage(
        platform: 'android',
        appVersion: '1.0.0',
        locale: 'vi-VN',
        padding: const EdgeInsets.fromLTRB(0, 24, 0, 48),
      );
      expect(msg, {
        'protocol': 1,
        'type': 'init',
        'platform': 'android',
        'appVersion': '1.0.0',
        'locale': 'vi-VN',
        'insets': {'top': 24.0, 'right': 0.0, 'bottom': 48.0, 'left': 0.0},
      });
      expect(
        receiveScript(insetsMessage(EdgeInsets.zero)),
        startsWith('window.fornav?.receive({"protocol":1,"type":"insets"'),
      );
    });

    test('onBack 결과는 플랫폼별 참 값을 모두 받는다', () {
      expect(isTrueResult(true), isTrue);
      expect(isTrueResult('true'), isTrue);
      expect(isTrueResult(1), isTrue);
      expect(isTrueResult(false), isFalse);
      expect(isTrueResult('false'), isFalse);
      expect(isTrueResult(null), isFalse);
    });
    group('googleSignIn', () {
      test('features가 비면 init에 넣지 않고, 있으면 그대로 담는다', () {
        Map<String, Object> init(List<String> features) => initMessage(
          platform: 'ios',
          appVersion: '1.0.0',
          locale: 'en-US',
          padding: EdgeInsets.zero,
          features: features,
        );
        expect(init(const []).containsKey('features'), isFalse);
        expect(init(const [featureGoogleSignIn])['features'], ['googleSignIn']);
      });

      test('googleSignInResult는 성공이면 idToken, 실패면 error 하나만 담는다', () {
        expect(googleSignInSuccess('eyJ.test.sig'), {
          'protocol': 1,
          'type': 'googleSignInResult',
          'idToken': 'eyJ.test.sig',
        });
        expect(googleSignInFailure(canceled: true), {'protocol': 1, 'type': 'googleSignInResult', 'error': 'canceled'});
        expect(googleSignInFailure(canceled: false), {'protocol': 1, 'type': 'googleSignInResult', 'error': 'failed'});
      });

      test('사용자가 닫은 것만 canceled다', () {
        expect(isSignInCanceled(const GoogleSignInException(code: GoogleSignInExceptionCode.canceled)), isTrue);
        expect(isSignInCanceled(const GoogleSignInException(code: GoogleSignInExceptionCode.interrupted)), isFalse);
        expect(
          isSignInCanceled(const GoogleSignInException(code: GoogleSignInExceptionCode.clientConfigurationError)),
          isFalse,
        );
        expect(isSignInCanceled(Exception('network')), isFalse);
      });

      test('Android는 웹 클라이언트 ID만, iOS는 iOS 클라이언트 ID도 있어야 켠다', () {
        expect(nativeSignInConfigured(isIOS: false, webClientId: 'w', iosClientId: ''), isTrue);
        expect(nativeSignInConfigured(isIOS: true, webClientId: 'w', iosClientId: ''), isFalse);
        expect(nativeSignInConfigured(isIOS: true, webClientId: 'w', iosClientId: 'i'), isTrue);
        expect(nativeSignInConfigured(isIOS: false, webClientId: '', iosClientId: 'i'), isFalse);
      });
    });
  });

  group('통화 매체(backlog 04)', () {
    test('speechStart의 lang이 없거나 비면 무시한다', () {
      expect(speechLangOf({'type': 'speechStart', 'lang': 'vi-VN'}), 'vi-VN');
      expect(speechLangOf({'type': 'speechStart', 'lang': '  '}), isNull);
      expect(speechLangOf({'type': 'speechStart'}), isNull);
    });

    test('speech·speechError 형식', () {
      expect(speechMessage('xin chào', isFinal: true), {
        'protocol': 1,
        'type': 'speech',
        'text': 'xin chào',
        'final': true,
      });
      expect(speechErrorMessage(SpeechErrorKind.denied), {'protocol': 1, 'type': 'speechError', 'error': 'denied'});
    });

    test('권한·언어 오류는 바로 끄고, 말 없음은 세지 않고, 그 밖은 이어지면 끈다', () {
      expect(speechErrorKind('error_permission', errorsInRow: 1), SpeechErrorKind.denied);
      expect(speechErrorKind('error_language_not_supported', errorsInRow: 1), SpeechErrorKind.unsupported);
      expect(speechErrorKind('error_no_match', errorsInRow: 99), isNull);
      expect(speechErrorKind('error_network', errorsInRow: 1), isNull);
      expect(speechErrorKind('error_network', errorsInRow: speechMaxErrorsInRow), SpeechErrorKind.unsupported);
      expect(speechErrorCounts('error_no_match'), isFalse);
      expect(speechErrorCounts('error_client'), isTrue);
    });

    test('WebView 권한 요청은 마이크만 허용한다', () {
      expect(isMicrophoneOnlyRequest({'microphone'}), isTrue);
      expect(isMicrophoneOnlyRequest({'microphone', 'camera'}), isFalse);
      expect(isMicrophoneOnlyRequest({}), isFalse);
    });

    test('파일 선택기는 사진을 받는 input에서만 연다', () {
      expect(acceptsImages(['image/*']), isTrue);
      expect(acceptsImages(['']), isTrue);
      expect(acceptsImages(['image/png,image/jpeg']), isTrue);
      expect(acceptsImages(['application/pdf']), isFalse);
    });
  });
  group('push(app-front backlog 07)', () {
    test('pushToken·pushOpen 메시지', () {
      expect(pushTokenMessage('t'), {'protocol': 1, 'type': 'pushToken', 'token': 't'});
      expect(pushTokenFailure(denied: true), {'protocol': 1, 'type': 'pushToken', 'error': 'denied'});
      expect(pushTokenFailure(denied: false), {'protocol': 1, 'type': 'pushToken', 'error': 'failed'});
      expect(pushOpenMessage('C-251031-001'), {'protocol': 1, 'type': 'pushOpen', 'caseId': 'C-251031-001'});
    });

    test('센터 알림의 사례 id 모양만 연다', () {
      expect(pushCaseIdOf({'kind': 'center', 'caseId': 'C-251031-001'}), 'C-251031-001');
      expect(pushCaseIdOf({'kind': 'center', 'caseId': 'C-02'}), 'C-02');
      expect(pushCaseIdOf({'kind': 'call', 'caseId': 'C-02'}), isNull);
      expect(pushCaseIdOf({'caseId': 'C-02'}), isNull);
      expect(pushCaseIdOf({'kind': 'center'}), isNull);
      expect(pushCaseIdOf({'kind': 'center', 'caseId': 'javascript:alert(1)'}), isNull);
      expect(pushCaseIdOf({'kind': 'center', 'caseId': 'C-02</script>'}), isNull);
      expect(pushCaseIdOf({'kind': 'center', 'caseId': 'C-${'1' * 41}'}), isNull);
    });

    test('init 전에 누른 알림은 마지막 하나를 들고 있다가 init 뒤 한 번 보낸다', () {
      final gate = PushOpenGate();
      expect(gate.tap('C-01'), isNull);
      expect(gate.tap('C-02'), isNull);
      expect(gate.opened(), 'C-02');
      expect(gate.opened(), isNull);
      // init 뒤에는 곧바로 보낸다
      expect(gate.tap('C-03'), 'C-03');
      // 페이지가 다시 불리면(ready) 다음 init까지 다시 들고 있는다
      gate.close();
      expect(gate.tap('C-04'), isNull);
      expect(gate.opened(), 'C-04');
    });

    test('Firebase 값이 모두 있고 모양이 맞아야 push를 켠다', () {
      const key = 'AIzaSyA0123456789abcdefghijklmnopqrstuv';
      const androidId = '1:123:android:abc123';
      const iosId = '1:123:ios:def456';
      FirebaseOptions? opts({bool isIOS = false, String apiKey = key, String android = androidId, String ios = ''}) =>
          firebaseOptionsFor(
            isIOS: isIOS,
            apiKey: apiKey,
            appIdAndroid: android,
            appIdIos: ios,
            senderId: '123',
            projectId: 'p',
          );
      expect(opts()?.appId, androidId);
      expect(opts(apiKey: ''), isNull);
      // iOS는 iOS 앱 ID가 있어야 한다
      expect(opts(isIOS: true), isNull);
      expect(opts(isIOS: true, ios: iosId)?.appId, iosId);
      // 모양이 틀린 값은 iOS SDK가 앱을 멈추므로 켜지 않는다
      expect(opts(apiKey: 'AIzaSyShort'), isNull);
      expect(opts(android: 'abc'), isNull);
      expect(opts(isIOS: true, ios: androidId), isNull);
    });
  });
}
