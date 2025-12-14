declare namespace Mocha {
    interface Context {
        [key: string]: any;
    }
}

declare var describe: Mocha.SuiteFunction;
declare var it: Mocha.TestFunction;
declare var before: Mocha.HookFunction;
declare var beforeEach: Mocha.HookFunction;
declare var after: Mocha.HookFunction;
declare var afterEach: Mocha.HookFunction;
