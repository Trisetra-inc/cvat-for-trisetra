// Copyright (C) 2020-2022 Intel Corporation
// Copyright (C) 2022 CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import React, { useState, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { useHistory } from 'react-router';

import { Row, Col } from 'antd/lib/grid';
import Dropdown from 'antd/lib/dropdown';
import { PlusOutlined, UploadOutlined, LoadingOutlined } from '@ant-design/icons';
import Button from 'antd/lib/button';
import Input from 'antd/lib/input';
import { Modal } from 'antd';
import { importActions } from 'actions/import-actions';
import { SortingComponent, ResourceFilterHOC, defaultVisibility } from 'components/resource-sorting-filtering';
import { TasksQuery } from 'reducers';
import { usePrevious } from 'utils/hooks';
import { MultiPlusIcon } from 'icons';
import CvatDropdownMenuPaper from 'components/common/cvat-dropdown-menu-paper';
import { sendRequest } from 'trisetra-api-wrapper';
import {
    localStorageRecentKeyword, localStorageRecentCapacity, predefinedFilterValues, config,
} from './tasks-filter-configuration';

import dimensions from '../projects-page/dimensions';

const FilteringComponent = ResourceFilterHOC(
    config, localStorageRecentKeyword, localStorageRecentCapacity, predefinedFilterValues,
);

interface VisibleTopBarProps {
    onApplyFilter(filter: string | null): void;
    onApplySorting(sorting: string | null): void;
    onApplySearch(search: string | null): void;
    query: TasksQuery;
    importing: boolean;
}

export default function TopBarComponent(props: VisibleTopBarProps): JSX.Element {
    const dispatch = useDispatch();
    const {
        importing, query, onApplyFilter, onApplySorting, onApplySearch,
    } = props;
    const [visibility, setVisibility] = useState(defaultVisibility);
    const history = useHistory();
    const prevImporting = usePrevious(importing);

    // eslint-disable-next-line @typescript-eslint/explicit-function-return-type
    const updatePrebuilts = async (ev: React.MouseEvent<HTMLElement, MouseEvent>) => {
        ev.preventDefault();
        sendRequest('tasks/update-prebuilts').then((data) => {
            Modal.success({
                title: 'Updating Prebuilts ...',
                content: data.message,
            });
            if (data.redirect_url) {
                const redirectedTab = window.open(data.redirect_url, '_blank', 'noopener noreferrer');
                redirectedTab?.focus();
            }
        })
            .catch((error) => {
                Modal.error({
                    title: 'Error',
                    content: error.message,
                });
            });
    };

    // eslint-disable-next-line @typescript-eslint/explicit-function-return-type
    const updateFloorMaterials = async (ev: React.MouseEvent<HTMLElement, MouseEvent>) => {
        ev.preventDefault();
        sendRequest('tasks/update-floor-materials').then((data) => {
            Modal.success({
                title: 'Updating Floor Materials ...',
                content: data.message,
            });
            if (data.redirect_url) {
                const redirectedTab = window.open(data.redirect_url, '_blank', 'noopener noreferrer');
                redirectedTab?.focus();
            }
        })
            .catch((error) => {
                Modal.error({
                    title: 'Error',
                    content: error.message,
                });
            });
    };

    useEffect(() => {
        if (prevImporting && !importing) {
            onApplyFilter(query.filter);
        }
    }, [importing]);

    return (
        <Row className='cvat-tasks-page-top-bar' justify='center' align='middle'>
            <Col {...dimensions}>
                <div className='cvat-tasks-page-filters-wrapper'>
                    <Input.Search
                        enterButton
                        onSearch={(phrase: string) => {
                            onApplySearch(phrase);
                        }}
                        defaultValue={query.search || ''}
                        className='cvat-tasks-page-search-bar'
                        placeholder='Search ...'
                    />
                    <div>
                        <Button type='default' onClick={updatePrebuilts}>
                            Update Prebuilts
                        </Button>
                        <Button type='default' onClick={updateFloorMaterials}>
                            Update Floor Materials
                        </Button>
                        <SortingComponent
                            visible={visibility.sorting}
                            onVisibleChange={(visible: boolean) => (
                                setVisibility({ ...defaultVisibility, sorting: visible })
                            )}
                            defaultFields={query.sort?.split(',') || ['-ID']}
                            sortingFields={['ID', 'Owner', 'Status', 'Assignee', 'Updated date', 'Subset', 'Mode', 'Dimension', 'Project ID', 'Name', 'Project name']}
                            onApplySorting={onApplySorting}
                        />
                        <FilteringComponent
                            value={query.filter}
                            predefinedVisible={visibility.predefined}
                            builderVisible={visibility.builder}
                            recentVisible={visibility.recent}
                            onPredefinedVisibleChange={(visible: boolean) => (
                                setVisibility({ ...defaultVisibility, predefined: visible })
                            )}
                            onBuilderVisibleChange={(visible: boolean) => (
                                setVisibility({ ...defaultVisibility, builder: visible })
                            )}
                            onRecentVisibleChange={(visible: boolean) => (
                                setVisibility({ ...defaultVisibility, builder: visibility.builder, recent: visible })
                            )}
                            onApplyFilter={onApplyFilter}
                        />
                    </div>
                </div>
                <div>
                    <Dropdown
                        trigger={['click']}
                        overlay={(
                            <CvatDropdownMenuPaper>
                                <Button
                                    className='cvat-create-task-button'
                                    type='primary'
                                    onClick={(): void => history.push('/tasks/create')}
                                    icon={<PlusOutlined />}
                                >
                                    Create a new task
                                </Button>
                                <Button
                                    className='cvat-create-multi-tasks-button'
                                    type='primary'
                                    onClick={(): void => history.push('/tasks/create?many=true')}
                                    icon={<span className='anticon'><MultiPlusIcon /></span>}
                                >
                                    Create multi tasks
                                </Button>
                                <Button
                                    className='cvat-import-task-button'
                                    type='primary'
                                    disabled={importing}
                                    icon={<UploadOutlined />}
                                    onClick={() => dispatch(importActions.openImportBackupModal('task'))}
                                >
                                    Create from backup
                                    {importing && <LoadingOutlined />}
                                </Button>
                            </CvatDropdownMenuPaper>
                        )}
                    >
                        <Button type='primary' className='cvat-create-task-dropdown' icon={<PlusOutlined />} />
                    </Dropdown>
                </div>
            </Col>
        </Row>
    );
}
