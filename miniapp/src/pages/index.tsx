import { createRoute } from '@granite-js/react-native';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Txt, Top } from '@toss/tds-react-native';

export const Route = createRoute('/', {
  component: Page,
});

function Page() {
  const navigation = Route.useNavigation();

  return (
    <View style={styles.container}>
      <Top
        title={<Txt typography="t2" fontWeight="bold">PDF 한국어 맞춤법 검사기</Txt>}
        subtitle1={
          <Txt typography="t6" color="#6B7280">
            웹 서비스는 종료되었고, 이제 Toss 미니앱에서 제공됩니다.
          </Txt>
        }
      />

      <View style={styles.content}>
        <Button
          display="full"
          onPress={() => navigation.navigate('/about')}
        >
          시작하기
        </Button>
        <Button
          display="full"
          style="weak"
          type="dark"
          onPress={() => navigation.navigate('/about')}
          viewStyle={styles.secondaryButton}
        >
          이용 안내
        </Button>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 24,
    backgroundColor: 'white',
  },
  content: {
    marginTop: 28,
    gap: 10,
  },
  secondaryButton: {
    marginTop: 2,
  },
});
