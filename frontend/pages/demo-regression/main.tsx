import { mountPage } from "../../shared/mount";
import { PageRoot } from "../../shared/PageRoot";
import { Page } from "./Page";

mountPage(<PageRoot>{(page) => <Page page={page} />}</PageRoot>);
