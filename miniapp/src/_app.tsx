import { AppsInToss } from '@apps-in-toss/framework';
import React, { type PropsWithChildren } from 'react';
import { type InitialProps } from '@granite-js/react-native';
import { context } from '../require.context';

function AppContainer({ children }: PropsWithChildren<InitialProps>) {
  return <>{children}</>;
}

export default AppsInToss.registerApp(AppContainer, { context });
