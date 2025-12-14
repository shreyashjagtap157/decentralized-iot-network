import { Assertion } from 'chai';

declare global {
    namespace Chai {
        interface Assertion {
            emit(contract: any, eventName: string): Assertion;
            revertedWith(message: string): Assertion;
            closeTo(expected: any, delta: any): Assertion;
            gt(value: any): Assertion;
            lt(value: any): Assertion;
            withArgs(...args: any[]): Assertion;
        }
    }
}

export { };
